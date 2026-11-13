package steven.rangersnipers;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3dc;
import org.joml.Vector4dc;
import java.util.List;

/** Per-projectile physics-path state; never reads its owner's position. */
public final class FlightState implements Component<EntityStore> {
    public record Point(double distance, double multiplier) {
        public Point {
            if (!Double.isFinite(distance) || !Double.isFinite(multiplier) || distance < 0 ||
                multiplier <= 0 || multiplier > 1) throw new IllegalArgumentException("Invalid falloff point");
        }
    }
    public record Profile(String weaponId, String markerId, List<Point> points) {
        public Profile {
            points = List.copyOf(points);
            if (weaponId == null || markerId == null || points.size() < 2 ||
                points.get(0).distance() != 0 || points.get(0).multiplier() != 1)
                throw new IllegalArgumentException("Invalid flight profile");
            for (int i = 1; i < points.size(); i++)
                if (points.get(i).distance() <= points.get(i - 1).distance() ||
                    points.get(i).multiplier() > points.get(i - 1).multiplier())
                    throw new IllegalArgumentException("Falloff must have increasing distances and nonincreasing damage");
        }
        public double multiplier(double distance) {
            if (!Double.isFinite(distance) || distance < 0) throw new IllegalArgumentException("Invalid flight distance");
            for (int i = 1; i < points.size(); i++) {
                Point right = points.get(i), left = points.get(i - 1);
                if (distance <= right.distance()) {
                    double progress = (distance - left.distance()) / (right.distance() - left.distance());
                    return left.multiplier() + progress * (right.multiplier() - left.multiplier());
                }
            }
            return points.get(points.size() - 1).multiplier();
        }
    }
    private final Profile profile;
    private final double originX, originY, originZ;
    private double lastX, lastY, lastZ, pathLength;
    private double contactX, contactY, contactZ, impactDistance;
    private boolean impactFinished;
    private boolean impactClaimed;
    private boolean metadataContactAllowed;
    private boolean impactHookInstalled;
    private boolean predicted;

    public FlightState(Profile profile, Vector3dc origin) {
        this(profile, origin.x(), origin.y(), origin.z());
    }
    public FlightState(Profile profile, Vector3dc origin, boolean metadataContactAllowed, boolean predicted) {
        this(profile, origin);
        this.metadataContactAllowed=metadataContactAllowed;
        this.predicted=predicted;
    }
    public boolean isPredicted() { return predicted; }
    public boolean hasImpactHook() { return impactHookInstalled; }
    void markImpactHookInstalled() { impactHookInstalled=true; }
    /** Only server-dispatched native ProjectileHit metadata can use this fallback. */
    public double distanceForValidatedContact(Vector4dc contact) {
        if (!impactFinished && metadataContactAllowed)
            finishImpact(new org.joml.Vector3d(contact.x(),contact.y(),contact.z()));
        return distanceTo(contact);
    }
    private FlightState(Profile profile, double x, double y, double z) {
        if (profile == null || !Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z))
            throw new IllegalArgumentException("Invalid projectile origin");
        this.profile = profile;
        this.originX = this.lastX = x; this.originY = this.lastY = y; this.originZ = this.lastZ = z;
    }
    public Profile profile() { return profile; }
    /** Immutable launch origin copied for optional spatial audio; never a live transform. */
    public org.joml.Vector3d originCopy() { return new org.joml.Vector3d(originX,originY,originZ); }
    private double segment(double x, double y, double z) {
        double distance = Math.hypot(Math.hypot(x - lastX, y - lastY), z - lastZ);
        if (!Double.isFinite(distance)) throw new IllegalArgumentException("Invalid projectile path point");
        return distance;
    }
    /** Called after native physics; its simulated 3D segment includes gravity. */
    public void recordStep(Vector3dc position) {
        if (impactFinished) return;
        double nextLength = pathLength + segment(position.x(), position.y(), position.z());
        if (!Double.isFinite(nextLength)) throw new IllegalArgumentException("Invalid projectile path length");
        pathLength = nextLength;
        lastX = position.x(); lastY = position.y(); lastZ = position.z();
    }
    /** Native ImpactConsumer calls this before queuing ProjectileHit/Miss. */
    public void finishImpact(Vector3dc contact) {
        if (impactFinished) return;
        double distance = pathLength + segment(contact.x(), contact.y(), contact.z());
        if (!Double.isFinite(distance)) throw new IllegalArgumentException("Invalid projectile impact length");
        contactX = contact.x(); contactY = contact.y(); contactZ = contact.z();
        impactDistance = distance;
        impactFinished = true;
    }
    /** Requires the native hit metadata to agree with the frozen final contact. */
    public double distanceTo(Vector4dc contact) {
        if (!impactFinished) throw new IllegalStateException("Projectile impact was not finalized");
        double error = Math.hypot(Math.hypot(contact.x() - contactX, contact.y() - contactY), contact.z() - contactZ);
        if (!Double.isFinite(error) || error > 0.000001)
            throw new IllegalArgumentException("Projectile contact metadata mismatch");
        return impactDistance;
    }
    /** A nonpiercing sniper projectile may reach its native DamageEntity only once. */
    public boolean claimImpact() {
        if (!impactFinished || impactClaimed) return false;
        impactClaimed = true;
        return true;
    }
    @Override public FlightState clone() {
        FlightState copy = new FlightState(profile, originX, originY, originZ);
        copy.lastX = lastX; copy.lastY = lastY; copy.lastZ = lastZ; copy.pathLength = pathLength;
        copy.contactX = contactX; copy.contactY = contactY; copy.contactZ = contactZ;
        copy.impactDistance = impactDistance; copy.impactFinished = impactFinished; copy.impactClaimed = impactClaimed;
        copy.metadataContactAllowed=metadataContactAllowed;copy.impactHookInstalled=impactHookInstalled;copy.predicted=predicted;
        return copy;
    }
}
