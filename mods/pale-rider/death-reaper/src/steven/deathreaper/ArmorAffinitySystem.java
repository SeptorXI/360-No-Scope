package steven.deathreaper;

import com.airijko.endlessleveling.api.EndlessLevelingAPI;
import com.airijko.endlessleveling.EndlessLeveling;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.ItemArmorSlot;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.EnumMap;
import java.util.UUID;

/** Primary Necromancer affinity. Native armor resource/resistance bonuses live on the item assets. */
public final class ArmorAffinitySystem extends EntityTickingSystem<EntityStore> implements AutoCloseable {
    private final EndlessLevelingAPI api = EndlessLevelingAPI.get();
    private final AffinityLedger ledger = new AffinityLedger(api::setExternalAttributeBonus);
    @Override public Query<EntityStore> getQuery() { return Player.getComponentType(); }
    @Override public boolean isParallel(int count, int size) { return false; }

    public void refresh(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor, long nowMs) {
        if (ref == null || !ref.isValid() || accessor == null) return;
        var player = accessor.getComponent(ref, PlayerRef.getComponentType());
        var identity = accessor.getComponent(ref, UUIDComponent.getComponentType());
        UUID uuid = player != null ? player.getUuid() : identity != null ? identity.getUuid() : null;
        if (uuid == null) return;
        boolean alive = accessor.getComponent(ref, DeathComponent.getComponentType()) == null;
        var stats = accessor.getComponent(ref, EntityStatMap.getComponentType());
        var health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        alive &= health == null || health.get() > health.getMin();
        var armor = accessor.getComponent(ref, InventoryComponent.Armor.getComponentType());
        var container = armor == null ? null : armor.getInventory();
        if (reconcile(uuid, alive, container, nowMs)) {
            var plugin = EndlessLeveling.getInstance();
            var data = plugin == null ? null : plugin.getPlayerDataManager().get(uuid);
            var skill = plugin == null ? null : plugin.getSkillManager();
            if (data != null && skill != null) {
                // Native periodic resource refresh normally waits four seconds. Reconcile on the
                // actor's world tick only when eligibility changes; leave native math authoritative.
                skill.applyHealthModifiers(ref, accessor, data);
                skill.applyFlowModifiers(ref, accessor, data);
                skill.applyMovementSpeedModifier(ref, accessor, data);
            }
        }
    }
    /** Same entry used by ECS refresh and isolated native equipment integration fixtures. */
    public boolean reconcile(UUID uuid, boolean alive, ItemContainer armor, long nowMs) {
        String primary = api.getPrimaryClassId(uuid);
        boolean necromancer = primary != null && api.sharesClassPath(primary, "necromancer");
        return ledger.refresh(uuid, alive, necromancer, snapshot(armor), nowMs);
    }
    public static EnumMap<AffinityRules.Slot, AffinityRules.Worn> snapshot(ItemContainer container) {
        var worn = new EnumMap<AffinityRules.Slot, AffinityRules.Worn>(AffinityRules.Slot.class);
        if (container != null) for (var piece : AffinityRules.PIECES) {
            var slot = ItemArmorSlot.valueOf(piece.slot().name());
            short slotIndex = (short) slot.getValue();
            if (slotIndex < 0 || slotIndex >= container.getCapacity()) continue;
            var stack = container.getItemStack(slotIndex);
            if (stack == null || ItemStack.isEmpty(stack)) continue;
            var nativeArmor = stack.getItem().getArmor();
            worn.put(piece.slot(), new AffinityRules.Worn(stack.getItemId(), stack.getQuantity(), stack.isBroken(),
                nativeArmor != null && nativeArmor.getArmorSlot() == slot));
        }
        return worn;
    }
    @Override public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk,
                               Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        refresh(chunk.getReferenceTo(index), buffer, System.currentTimeMillis());
    }
    public void disconnect(UUID player) { ledger.remove(player, System.currentTimeMillis()); }
    @Override public void close() { ledger.close(); }
}
