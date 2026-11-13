package steven.rangersnipers;

import com.hypixel.hytale.protocol.Position;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.protocol.packets.world.PlaySoundEvent3D;
import org.joml.Vector3dc;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.BiConsumer;
import java.util.function.Consumer;
import java.util.function.LongSupplier;

/** Claims a paid discharge once. A shotgun's pellets share one shell token. */
public final class OwnerTailGate {
    private static final long BURST_GAP_NANOS = 180_000_000L;
    private final Map<Object, Long> seen = new LinkedHashMap<>();
    private final Map<Object, Long> recentBurstShots = new LinkedHashMap<>();
    private final Consumer<Throwable> diagnostic;
    private final LongSupplier clock;
    private long nextDiagnostic;

    public OwnerTailGate(Consumer<Throwable> diagnostic) {
        this(diagnostic, System::nanoTime);
    }

    public OwnerTailGate(Consumer<Throwable> diagnostic, LongSupplier clock) {
        this.diagnostic = diagnostic;
        this.clock = clock;
    }

    public boolean emit(Object shot, Object owner, int pelletIndex, boolean committedWeapon, int eventIndex,
                        Vector3dc origin, BiConsumer<Object, PlaySoundEvent3D> send) {
        if (eventIndex <= 0 || origin == null || !Double.isFinite(origin.x()) || !Double.isFinite(origin.y())
            || !Double.isFinite(origin.z())) return false;
        return emitOnce(shot, owner, pelletIndex, committedWeapon, () ->
            send.accept(owner, new PlaySoundEvent3D(eventIndex, SoundCategory.SFX,
                new Position(origin.x(), origin.y(), origin.z()), 1, 1)));
    }

    boolean emitOnce(Object shot, Object owner, int pelletIndex, boolean committedWeapon, Runnable send) {
        if (shot == null || owner == null || pelletIndex > 0 || !committedWeapon) return false;
        try {
            if (!claim(shot)) return false;
            send.run();
            return true;
        } catch (Throwable error) {
            warn(error);
            return false;
        }
    }

    private synchronized boolean claim(Object shot) {
        long now = clock.getAsLong();
        seen.entrySet().removeIf(entry -> now - entry.getValue() > 10_000_000_000L);
        if (seen.containsKey(shot)) return false;
        if (seen.size() >= 2048) seen.remove(seen.keySet().iterator().next());
        // Claim before dispatching. No packet sends hold the gate lock.
        seen.put(shot, now);
        return true;
    }

    synchronized boolean continuesBurst(Object owner, boolean burstPrimary) {
        if (!burstPrimary) {
            recentBurstShots.remove(owner);
            return false;
        }
        long now = clock.getAsLong();
        recentBurstShots.values().removeIf(previous -> now - previous > BURST_GAP_NANOS);
        return recentBurstShots.put(owner, now) != null;
    }

    public synchronized void warn(Throwable error) {
        try {
            long now = clock.getAsLong();
            if (now >= nextDiagnostic) {
                nextDiagnostic = now + 30_000_000_000L;
                diagnostic.accept(error);
            }
        } catch (Throwable ignored) {
        }
    }
}
