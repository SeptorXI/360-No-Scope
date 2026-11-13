package steven.rangersnipers;

import org.herolias.plugin.SimpleEnchanting;
import org.herolias.plugin.enchantment.*;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import java.lang.reflect.Field;
import java.util.UUID;

/** Narrow bridge for the exact required SimpleEnchantments 1.2.1 dependency. */
public final class EternalShotBridge {
    private final EnchantmentManager manager;
    private final EnchantmentEternalShotSystem upstream;
    public EternalShotBridge() throws ReflectiveOperationException {
        SimpleEnchanting plugin = SimpleEnchanting.getInstance();
        if (plugin == null || plugin.getEnchantmentManager() == null)
            throw new IllegalStateException("SimpleEnchantments 1.2.1 is not initialized");
        Field field = SimpleEnchanting.class.getDeclaredField("eternalShotSystem");
        field.setAccessible(true);
        upstream = (EnchantmentEternalShotSystem) field.get(plugin);
        manager = plugin.getEnchantmentManager();
        if (upstream == null) throw new IllegalStateException("Eternal Shot system is not initialized");
    }
    public boolean applies(ItemStack weapon) {
        // Native manager checks enabled configuration as well as stored level.
        return manager.categorizeItem(weapon) == ItemCategory.RANGED_WEAPON &&
               manager.getEnchantmentLevel(weapon, EnchantmentType.ETERNAL_SHOT) > 0;
    }
    public void clearUpstream(UUID playerId) { upstream.onSlotChanged(playerId); }
}
