package steven.rangersnipers;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.math.util.HashUtil;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.projectile.ProjectileModule;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import com.hypixel.hytale.server.core.modules.projectile.component.ProjectileLaunchContext;
import com.hypixel.hytale.server.core.modules.projectile.config.BallisticData;
import com.hypixel.hytale.server.core.modules.projectile.config.BallisticDataProvider;
import com.hypixel.hytale.server.core.modules.projectile.config.ProjectileConfig;
import com.hypixel.hytale.server.core.modules.projectile.event.ProjectileLaunchEvent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.TargetUtil;

/** A native projectile whose terrain and entity contacts are resolved by the server. */
public class ServerProjectileInteraction extends SimpleInstantInteraction implements BallisticDataProvider {
    public static final BuilderCodec<ServerProjectileInteraction> CODEC = BuilderCodec.builder(
        ServerProjectileInteraction.class, ServerProjectileInteraction::new, SimpleInstantInteraction.CODEC)
        .appendInherited(new KeyedCodec<>("Config", Codec.STRING), (interaction, value) -> interaction.configId = value,
            interaction -> interaction.configId, (interaction, parent) -> interaction.configId = parent.configId)
        .addValidator(ProjectileConfig.VALIDATOR_CACHE.getValidator().late()).add()
        .appendInherited(new KeyedCodec<>("Lifetime", Codec.FLOAT), (interaction, value) -> interaction.lifetime = value,
            interaction -> interaction.lifetime, (interaction, parent) -> interaction.lifetime = parent.lifetime).add()
        .appendInherited(new KeyedCodec<>("IgnorePitch", Codec.BOOLEAN), (interaction, value) -> interaction.ignorePitch = value,
            interaction -> interaction.ignorePitch, (interaction, parent) -> interaction.ignorePitch = parent.ignorePitch).add()
        .appendInherited(new KeyedCodec<>("IgnoreYaw", Codec.BOOLEAN), (interaction, value) -> interaction.ignoreYaw = value,
            interaction -> interaction.ignoreYaw, (interaction, parent) -> interaction.ignoreYaw = parent.ignoreYaw).add()
        .appendInherited(new KeyedCodec<>("IgnoreRoll", Codec.BOOLEAN), (interaction, value) -> interaction.ignoreRoll = value,
            interaction -> interaction.ignoreRoll, (interaction, parent) -> interaction.ignoreRoll = parent.ignoreRoll).add()
        .build();

    private String configId;
    private float lifetime;
    private boolean ignorePitch, ignoreYaw, ignoreRoll;

    public ProjectileConfig getConfig() {
        return configId == null ? null : ProjectileConfig.getAssetMap().getAsset(configId);
    }

    @Override public BallisticData getBallisticData() {
        return getConfig();
    }

    @Override public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }

    @Override protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        // The native Simple interaction carries the effects. Only firstRun creates the projectile.
    }

    @Override protected final void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        var commands = context.getCommandBuffer();
        var source = context.getEntity();
        var owner = context.getOwningEntity();
        var heldItem = context.getHeldItem();
        var config = getConfig();
        if (commands == null || source == null || !source.isValid() || owner == null || !owner.isValid()
            || heldItem == null || heldItem.getItem().getWeapon() == null || config == null
            || !Float.isFinite(lifetime) || lifetime <= 0) {
            context.getState().state = InteractionState.Failed;
            return;
        }

        var look = TargetUtil.getLook(source, commands);
        if (ignorePitch) look.getRotation().setPitch(0);
        if (ignoreYaw) look.getRotation().setYaw(0);
        if (ignoreRoll) look.getRotation().setRoll(0);
        launchProjectiles(type, context, config, look);
    }

    protected void launchProjectiles(InteractionType type, InteractionContext context, ProjectileConfig config, Transform look) {
        var commands = context.getCommandBuffer();
        var owner = context.getOwningEntity();
        var modifiers = ImpactModifiers.collect(context, owner, commands);
        var projectile = ProjectileModule.get().spawnProjectile(null, launchSeed(context), owner, commands, config,
            look.getPosition(), look.getDirection(), (long)(lifetime * 1000));
        var launch = new ProjectileLaunchContext(type, true);
        registerProjectile(commands, context.getEntity(), projectile, modifiers, launch, null, true);
    }

    protected final float lifetimeSeconds() {
        return lifetime;
    }

    protected static Long launchSeed(InteractionContext context) {
        var chain = context.getChain();
        var entry = context.getEntry();
        return chain == null || entry == null ? null : HashUtil.hash((long)chain.getChainId(), (long)entry.getIndex());
    }

    protected static void registerProjectile(CommandBuffer<EntityStore> commands, Ref<EntityStore> eventSource,
                                               Ref<EntityStore> projectile, ImpactModifiers modifiers,
                                               ProjectileLaunchContext launch, ScatterPellet pellet, boolean announce) {
        commands.run(store -> {
            if (!projectile.isValid()) return;
            if (pellet != null) store.addComponent(projectile, RangerSnipersPlugin.scatterType, pellet);
            if (modifiers != null) store.putComponent(projectile, ImpactModifiers.getComponentType(), modifiers);
            store.putComponent(projectile, ProjectileLaunchContext.getComponentType(), launch);
        });
        if (announce) commands.invoke(eventSource,
            new ProjectileLaunchEvent(projectile, launch.getInteractionType(), launch.isLaunchedByWeapon()));
    }
}
