package steven.blacktempest;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/** Replaces only this addon's named sources. Short native leases bound missed disconnect cleanup. */
public final class AffinityLedger implements AutoCloseable {
    @FunctionalInterface public interface Sink {
        boolean set(UUID player, String attribute, String source, double amount, long expiresAtMs);
    }
    private record Applied(int mask, long refreshAtMs) {}
    private final Sink sink;
    private final Map<UUID, Applied> applied = new HashMap<>();
    private boolean closed;
    public AffinityLedger(Sink sink) { this.sink = java.util.Objects.requireNonNull(sink); }

    /** The equipment map contains actual worn slots, never hotbar/storage searches. */
    public synchronized boolean refresh(UUID player, boolean alive, boolean primaryMage,
                                     Map<AffinityRules.Slot, AffinityRules.Worn> equipment, long nowMs) {
        if (closed || player == null) return false;
        int mask = 0;
        for (int i = 0; i < AffinityRules.PIECES.size(); i++) {
            var piece = AffinityRules.PIECES.get(i);
            if (AffinityRules.eligible(piece, equipment == null ? null : equipment.get(piece.slot()), alive, primaryMage)) mask |= 1 << i;
        }
        var previous = applied.get(player);
        // There is no owned source to clear for a player who has never worn an eligible piece.
        if (previous == null && mask == 0) return false;
        if (previous != null && previous.mask() == mask && nowMs < previous.refreshAtMs()) return false;
        boolean transition = previous == null || previous.mask() != mask;
        boolean accepted = write(player, mask, nowMs);
        if (mask == 0 && accepted) applied.remove(player);
        else applied.put(player, new Applied(accepted ? mask : -1, accepted ? nowMs + AffinityRules.REFRESH_MS : nowMs));
        return transition;
    }

    private boolean write(UUID player, int mask, long nowMs) {
        boolean accepted = true;
        for (int i = 0; i < AffinityRules.PIECES.size(); i++) {
            var piece = AffinityRules.PIECES.get(i);
            boolean enabled = (mask & (1 << i)) != 0;
            for (var bonus : piece.bonuses()) {
                // The API takes an absolute epoch-millisecond deadline, not a duration.
                accepted &= sink.set(player, bonus.attribute(), piece.source(), enabled ? bonus.amount() : 0,
                    enabled ? nowMs + AffinityRules.LEASE_MS : Math.max(1, nowMs - 1));
            }
        }
        return accepted;
    }

    public synchronized void remove(UUID player, long nowMs) {
        if (player != null && applied.remove(player) != null) write(player, 0, nowMs);
    }
    public synchronized int trackedPlayers() { return applied.size(); }
    @Override public synchronized void close() {
        if (closed) return;
        closed = true;
        long now = System.currentTimeMillis();
        for (var player : applied.keySet()) write(player, 0, now);
        applied.clear();
    }
}
