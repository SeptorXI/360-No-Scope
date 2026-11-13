package steven.deathreaper;

import java.util.List;

/** Native bonuses, separate from skill allocation: Strength/Sorcery/Haste are percentage points;
 * Flow and Life Force are additive resource points in the installed Endless Leveling API. */
public final class AffinityRules {
    public static final long REFRESH_MS = 1_000;
    public static final long LEASE_MS = 3_000;
    public enum Slot { Head, Chest, Hands, Legs }
    public record Bonus(String attribute, double amount) {}
    public record Piece(Slot slot, String itemId, String source, List<Bonus> bonuses) {}
    public record Worn(String itemId, int quantity, boolean broken, boolean nativeSlotMatches) {}
    public static final List<Piece> PIECES = List.of(
        new Piece(Slot.Head, "DR_Death_Veil", "death_reaper_head", List.of(new Bonus("sorcery", 5), new Bonus("flow", 3))),
        new Piece(Slot.Chest, "DR_Reaper_Mantle", "death_reaper_chest", List.of(new Bonus("sorcery", 4), new Bonus("life_force", 4))),
        new Piece(Slot.Hands, "DR_Harvester_Grasp", "death_reaper_hands", List.of(new Bonus("strength", 4), new Bonus("sorcery", 4))),
        new Piece(Slot.Legs, "DR_Pale_Rider_Strides", "death_reaper_legs", List.of(new Bonus("flow", 3), new Bonus("haste", 3)))
    );
    private AffinityRules() {}
    public static boolean eligible(Piece piece, Worn worn, boolean alive, boolean primaryNecromancer) {
        return alive && primaryNecromancer && worn != null && piece.itemId().equals(worn.itemId())
            && worn.quantity() == 1 && !worn.broken() && worn.nativeSlotMatches();
    }
}
