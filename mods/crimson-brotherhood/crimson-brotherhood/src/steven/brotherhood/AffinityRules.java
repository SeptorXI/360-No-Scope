package steven.brotherhood;

import java.util.List;

/** Native external attributes: Strength/Haste use percentage-point bonus channels; Precision
 * adds critical-chance points, Ferocity adds critical-damage points, Life Force adds Health. */
public final class AffinityRules {
    public static final long REFRESH_MS = 1_000;
    public static final long LEASE_MS = 3_000;
    public enum Slot { Head, Chest, Hands, Legs }
    public record Bonus(String attribute, double amount) {}
    public record Piece(Slot slot, String itemId, String source, List<Bonus> bonuses) {}
    public record Worn(String itemId, int quantity, boolean broken, boolean nativeSlotMatches) {}
    public static final List<Piece> PIECES = List.of(
        new Piece(Slot.Head, "CB_Crimson_Cowl", "crimson_brotherhood_head", List.of(new Bonus("precision", 4), new Bonus("ferocity", 4))),
        new Piece(Slot.Chest, "CB_Oathbound_Shroud", "crimson_brotherhood_chest", List.of(new Bonus("life_force", 6))),
        new Piece(Slot.Hands, "CB_Silence_Grasp", "crimson_brotherhood_hands", List.of(new Bonus("strength", 8))),
        new Piece(Slot.Legs, "CB_Nightstalker_Strides", "crimson_brotherhood_legs", List.of(new Bonus("haste", 8)))
    );
    private AffinityRules() {}
    public static boolean eligible(Piece piece, Worn worn, boolean alive, boolean primaryAssassin) {
        return alive && primaryAssassin && worn != null && piece.itemId().equals(worn.itemId())
            && worn.quantity() == 1 && !worn.broken() && worn.nativeSlotMatches();
    }
}
