package steven.rangersnipers;

import com.hypixel.hytale.codec.*;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.*;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.*;
import com.hypixel.hytale.server.core.inventory.container.*;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.*;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;

public final class ChamberInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<ChamberInteraction> CODEC = BuilderCodec.builder(ChamberInteraction.class,
        ChamberInteraction::new, SimpleInstantInteraction.CODEC)
        .append(new KeyedCodec<>("Operation", Codec.STRING), (o,v)->o.operation=v, o->o.operation).add()
        .append(new KeyedCodec<>("WeaponId", Codec.STRING), (o,v)->o.weaponId=v, o->o.weaponId).add()
        .append(new KeyedCodec<>("Cost", Codec.INTEGER), (o,v)->o.cost=v, o->o.cost).add().build();
    private static final MetaKey<ChamberTransactions.Token> TOKEN = com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction.CONTEXT_META_REGISTRY.registerMetaObject();
    private String operation;
    private String weaponId;
    private int cost = 1;
    public ChamberInteraction() {}
    @Override public WaitForDataFrom getWaitForDataFrom() { return WaitForDataFrom.Server; }
    @Override protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        // Native NPC/local prediction also walks these operations. Only the
        // authoritative server branch may debit rounds or commit reload tokens.
        // The base simulator follows the synchronized server result afterwards.
    }
    @Override protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        try {
            if (!"Sync".equals(operation) && RangerSnipersPlugin.eternalShot == null) { fail(context); return; }
            var buffer = context.getCommandBuffer();
            var owner = context.getOwningEntity();
            if (buffer == null || owner == null || !owner.isValid()) { fail(context); return; }
            var hotbar = buffer.getComponent(owner, InventoryComponent.Hotbar.getComponentType());
            var profile = RangerSnipersPlugin.PROFILES.get(weaponId);
            var container = context.getHeldItemContainer();
            short slot = context.getHeldItemSlot();
            if (profile == null || hotbar == null || hotbar.getActiveSlot() != slot ||
                hotbar.getInventory() != container) { fail(context); return; }
            ItemStack weapon = container.getItemStack(slot);
            if (weapon == null || !weapon.getItemId().equals(weaponId) || weapon.isBroken()) { fail(context); return; }
            var reserve = InventoryComponent.getCombined(buffer, owner, InventoryComponent.HOTBAR_STORAGE_BACKPACK);
            switch (operation) {
                case "BeginReload" -> {
                    var state = ChamberState.read(weapon, profile);
                    int planned = Math.min(profile.capacity() - state.loaded(), ChamberTransactions.reserveCount(reserve, profile.ammoId()));
                    if (planned < 1) { fail(context); return; }
                    ItemStack initialized = ChamberState.initialize(weapon, profile);
                    if (initialized != weapon && !ChamberTransactions.replaceExact(container, slot, weapon, initialized)) { fail(context); return; }
                    context.setHeldItem(initialized);
                    context.getMetaStore().putMetaObject(TOKEN, ChamberTransactions.reloadToken(initialized, profile, planned));
                    mirror(context, initialized, profile);
                }
                case "DoubleReloadCondition" -> {
                    var token = context.getMetaStore().getIfPresentMetaObject(TOKEN);
                    if (token == null || token.plannedTransfer() != 2 ||
                        !ChamberTransactions.matches(weapon, profile, token) ||
                        profile.capacity() - ChamberState.read(weapon, profile).loaded() != 2 ||
                        ChamberTransactions.reserveCount(reserve, profile.ammoId()) < 2) fail(context);
                }
                case "ReloadCountCondition" -> {
                    var token = context.getMetaStore().getIfPresentMetaObject(TOKEN);
                    if (token == null || token.plannedTransfer() != cost ||
                        !ChamberTransactions.matches(weapon, profile, token)) fail(context);
                }
                case "CommitReload" -> {
                    var token = context.getMetaStore().removeMetaObject(TOKEN);
                    var result = ChamberTransactions.reload(container, slot, reserve, profile, token);
                    if (!result.committed()) { fail(context); return; }
                    context.setHeldItem(result.weapon());
                    mirror(context, result.weapon(), profile);
                }
                case "Consume" -> {
                    var uuid = buffer.getComponent(owner, UUIDComponent.getComponentType());
                    if (uuid == null || cost < 1 || cost > profile.capacity()) { fail(context); return; }
                    var state = ChamberState.read(weapon, profile);
                    if (state.instanceId() == null || state.loaded() < cost) { fail(context); return; }
                    var token = ChamberTransactions.token(weapon, profile);
                    boolean refund = RangerSnipersPlugin.eternalShot.applies(weapon);
                    // Clear/validate the pinned bridge before changing loaded rounds.
                    RangerSnipersPlugin.eternalShot.clearUpstream(uuid.getUuid());
                    var result = ChamberTransactions.fire(container, slot, profile, token, cost, refund);
                    if (!result.committed()) { fail(context); return; }
                    context.setHeldItem(result.weapon());
                    mirror(context, result.weapon(), profile);
                    if (result.refund() != null)
                        SimpleItemContainer.addOrDropItemStack(buffer, owner, reserve, result.refund());
                }
                case "Sync" -> mirror(context, weapon, profile);
                default -> fail(context);
            }
        } catch (RuntimeException failure) {
            RangerSnipersPlugin.reportFailure(weaponId, failure);
            fail(context);
        }
    }
    private static void fail(InteractionContext context) { context.getState().state = InteractionState.Failed; }
    private static void mirror(InteractionContext context, ItemStack weapon, ChamberState.Profile profile) {
        var stats = context.getCommandBuffer().getComponent(context.getOwningEntity(), EntityStatMap.getComponentType());
        if (stats != null && stats.get(DefaultEntityStatTypes.getAmmo()) != null)
            stats.setStatValue(DefaultEntityStatTypes.getAmmo(), ChamberState.read(weapon, profile).loaded());
    }
}
