package steven.blacktempest;

import java.util.List;

/** Named native external attributes, separate from saved allocations. Each worn slot is independent. */
public final class AffinityRules {
    public static final long REFRESH_MS = 1_000;
    public static final long LEASE_MS = 3_000;
    public enum Slot { Head, Chest, Hands, Legs }
    public record Bonus(String attribute, double amount) {}
    public record Piece(Slot slot, String itemId, String source, List<Bonus> bonuses) {}
    public record Worn(String itemId, int quantity, boolean broken, boolean nativeSlotMatches) {}
    public static final List<Piece> PIECES = List.of(
        new Piece(Slot.Head, "BT_Tyrants_Cowl", "black_tempest_head", List.of(new Bonus("sorcery", 8))),
        new Piece(Slot.Chest, "BT_Dominion_Mantle", "black_tempest_chest", List.of(new Bonus("flow", 8))),
        new Piece(Slot.Hands, "Weapon_Gauntlets_AB_Tickle_Time", "black_tempest_hands", List.of(new Bonus("haste", 6))),
        new Piece(Slot.Legs, "BT_Stormbound_Strides", "black_tempest_legs", List.of(new Bonus("life_force", 8)))
    );
    /** Existing ABTT Hands contributes affinity only; it is never class-gated, moved or rewritten. */
    public static final List<Piece> GATED_PIECES=PIECES.stream().filter(piece->piece.slot()!=Slot.Hands).toList();
    private AffinityRules() {}
    public static boolean eligible(Piece piece, Worn worn, boolean alive, boolean primaryMage) {
        return alive && primaryMage && worn != null && piece.itemId().equals(worn.itemId())
            && worn.quantity() == 1 && !worn.broken() && worn.nativeSlotMatches();
    }
}
