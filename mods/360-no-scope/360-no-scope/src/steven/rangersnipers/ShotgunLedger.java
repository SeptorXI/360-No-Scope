package steven.rangersnipers;

import java.util.*;

/** One shell's short-lived, bounded hit budget. Never static or player-global. */
public final class ShotgunLedger {
    public static final double GATHER_SECONDS = 0.1;
    public static final class Bucket {
        private final Set<Integer> pellets = new HashSet<>();
        private double damage;
        private boolean closed;
        public double damage() { return damage; }
        public int count() { return pellets.size(); }
    }
    public record Record(Bucket bucket, boolean leader, boolean accepted) {}
    private final int maximum;
    private final double perPelletMaximum;
    private final Map<Object, Bucket> targets = new HashMap<>();
    public ShotgunLedger(int maximum, double perPelletMaximum) {
        if (maximum < 2 || maximum > 12 || !Double.isFinite(perPelletMaximum) || perPelletMaximum <= 0)
            throw new IllegalArgumentException("Invalid scatter budget");
        this.maximum=maximum; this.perPelletMaximum=perPelletMaximum;
    }
    public Record record(Object target, int pellet, double damage) {
        if (target == null || pellet < 0 || pellet >= maximum || !Double.isFinite(damage) || damage <= 0 ||
            damage > perPelletMaximum + 0.000001) throw new IllegalArgumentException("Invalid scatter hit");
        Bucket bucket=targets.computeIfAbsent(target, ignored -> new Bucket());
        if (bucket.closed || !bucket.pellets.add(pellet)) return new Record(bucket,false,false);
        boolean leader=bucket.pellets.size()==1;
        bucket.damage += damage;
        return new Record(bucket,leader,true);
    }
    public double close(Bucket bucket) {
        if (bucket == null || bucket.closed || !targets.containsValue(bucket))
            throw new IllegalStateException("Scatter target already committed");
        bucket.closed=true;
        return bucket.damage;
    }
}
