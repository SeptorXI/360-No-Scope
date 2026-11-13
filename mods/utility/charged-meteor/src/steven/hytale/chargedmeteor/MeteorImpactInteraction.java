package steven.hytale.chargedmeteor;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import com.hypixel.hytale.server.core.util.TargetUtil;

public final class MeteorImpactInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<MeteorImpactInteraction> CODEC = BuilderCodec.builder(
            MeteorImpactInteraction.class, MeteorImpactInteraction::new, SimpleInstantInteraction.CODEC)
            .build();

    private static final double BASE_RADIUS = 12;
    private static final double BASE_CENTER_RADIUS = 4;

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        // Only the server selects and hits creatures.
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        var buffer = context.getCommandBuffer();
        var proxy = context.getEntity();
        var caster = context.getOwningEntity();
        if (buffer == null || proxy == null || !proxy.isValid() || caster == null || !caster.isValid()) {
            return;
        }

        var transform = buffer.getComponent(proxy, TransformComponent.getComponentType());
        var roots = RootInteraction.getAssetMap();
        var outerHit = roots.getAsset("ChargedMeteor_HitRoot");
        var centerHit = roots.getAsset("ChargedMeteor_CenterHitRoot");
        if (transform == null || outerHit == null || centerHit == null) {
            return;
        }
        var modifiers = ImpactModifiers.resolve(context, proxy, buffer);
        double scale = modifiers == null ? 1 : modifiers.getAttribute("AoeScale", 1f);
        double radius = BASE_RADIUS * scale;
        if (!Double.isFinite(radius) || radius <= 0) {
            return;
        }

        // Ability proxies have no remote client. Resolve the impact volume on the server,
        // then use the native per-target damage and Burn interactions with caster attribution.
        var center = transform.getPosition();
        double radiusSquared = radius * radius;
        double centerRadius = BASE_CENTER_RADIUS * scale;
        double centerRadiusSquared = centerRadius * centerRadius;
        // The spatial search excludes its exact boundary. The distance check below includes it.
        for (var target : TargetUtil.getAllEntitiesInSphere(center, radius + 1, buffer)) {
            if (caster.equals(target) || !LivingTargetInteraction.canHitCreature(target, buffer)) {
                continue;
            }
            var targetTransform = buffer.getComponent(target, TransformComponent.getComponentType());
            if (targetTransform == null) {
                continue;
            }
            double distanceSquared = center.distanceSquared(targetTransform.getPosition());
            if (distanceSquared > radiusSquared) {
                continue;
            }
            var targetContext = context.duplicate();
            targetContext.getMetaStore().putMetaObject(TARGET_ENTITY, target);
            context.fork(targetContext, distanceSquared <= centerRadiusSquared ? centerHit : outerHit, false);
        }
    }
}
