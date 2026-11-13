package steven.armordisplays;

import com.hypixel.hytale.protocol.ItemArmorSlot;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.SimpleItemContainer;
import com.hypixel.hytale.server.core.inventory.container.filter.FilterActionType;
import com.hypixel.hytale.server.core.inventory.container.filter.FilterType;
import com.hypixel.hytale.server.core.inventory.container.filter.SlotFilter;
import java.util.Arrays;

/** Native slot policies. Removal/drop always remain possible for legacy items. */
public final class DisplayRules {
    private DisplayRules() {}
    public static int capacity(String kind) {
        return switch (kind) { case "Stand" -> 6; case "Holder" -> 1; case "Rack" -> 3;
            default -> throw new IllegalArgumentException("Unknown display kind: " + kind); };
    }
    public static boolean accepts(String kind, int slot, ItemStack stack) {
        if (slot < 0 || slot >= capacity(kind) || stack == null || stack.isEmpty() || stack.getQuantity() != 1)
            return false;
        Item item = stack.getItem();
        if (item == null || !stack.isValid()) return false;
        if ("Stand".equals(kind) && slot < 4)
            return item.getArmor() != null && item.getArmor().getArmorSlot() == ItemArmorSlot.VALUES[slot];
        // Utility defaults also exist on building blocks; native shields already
        // declare Weapon and Items.Weapons, so generic utility is not evidence.
        return item.getWeapon() != null || (item.getCategories() != null
            && Arrays.stream(item.getCategories()).anyMatch(v -> v.startsWith("Items.Weapons")));
    }
    public static void configure(String kind, SimpleItemContainer container) {
        int expected = capacity(kind);
        if (container.getCapacity() != expected) {
            container.setGlobalFilter(FilterType.ALLOW_OUTPUT_ONLY);
            throw new IllegalArgumentException(kind + " inventory must have " + expected + " slots");
        }
        container.setGlobalFilter(FilterType.ALLOW_ALL);
        for (short slot=0; slot<expected; slot++) {
            final short index = slot;
            container.setSlotFilter(FilterActionType.ADD, slot, (action,c,s,item) -> {
                if(!accepts(kind,index,item)) return false;
                ItemStack existing=c.getItemStack(s);
                // Filter receives the incoming item, not the resulting merged stack.
                // Allow real swaps; never merge a second stackable weapon into a slot.
                return ItemStack.isEmpty(existing) || !existing.isStackableWith(item);
            });
            container.setSlotFilter(FilterActionType.REMOVE, slot, SlotFilter.ALLOW);
            container.setSlotFilter(FilterActionType.DROP, slot, SlotFilter.ALLOW);
        }
    }
    /** A visual must never authorize a real transfer or change the saved source. */
    public static ItemStack visualStack(ItemStack source) {
        return source == null || source.isEmpty() ? null : source.withQuantity(1);
    }
}
