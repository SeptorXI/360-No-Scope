package steven.hytale.chargedmeteor;

import com.hypixel.hytale.builtin.abilities.entity.AbilityEntityRepeat;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.model.config.Model;
import com.hypixel.hytale.server.core.asset.type.model.config.ModelAsset;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.InteractionManager;
import com.hypixel.hytale.server.core.modules.collision.CollisionMath;
import com.hypixel.hytale.server.core.modules.entity.DespawnComponent;
import com.hypixel.hytale.server.core.modules.entity.EntityModule;
import com.hypixel.hytale.server.core.modules.entity.component.BoundingBox;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.component.ModelComponent;
import com.hypixel.hytale.server.core.modules.entity.component.PersistentModel;
import com.hypixel.hytale.server.core.modules.entity.component.ProjectilePassthrough;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.tracker.NetworkId;
import com.hypixel.hytale.server.core.modules.interaction.InteractionModule;
import com.hypixel.hytale.server.core.modules.interaction.InteractionSimulationHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import com.hypixel.hytale.server.core.modules.time.TimeResource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.TargetUtil;
import org.joml.Vector3d;

public final class AimedMeteorInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<AimedMeteorInteraction> CODEC = BuilderCodec.builder(
            AimedMeteorInteraction.class, AimedMeteorInteraction::new, SimpleInstantInteraction.CODEC)
            .build();

    private static final double AIM_RANGE = 24.0;
    private static final float LIFETIME_SECONDS = 5f;
    private static final String FALL_ROOT = "ChargedMeteor_FallRoot";
    private static final String FALL_MODEL = "ChargedMeteor_Falling";

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        // Only the authoritative cast spawns the meteor.
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        var buffer = context.getCommandBuffer();
        var caster = context.getOwningEntity();
        if (buffer == null || caster == null || !caster.isValid()) {
            context.getState().state = InteractionState.Failed;
            return;
        }

        var position = resolveImpact(caster, buffer);
        var modelAsset = ModelAsset.getAssetMap().getAsset(FALL_MODEL);
        if (position == null || modelAsset == null) {
            context.getState().state = InteractionState.Failed;
            return;
        }

        var model = Model.createScaledModel(modelAsset, 1f, null);
        var holder = EntityStore.REGISTRY.newHolder();
        var rotation = new Rotation3f();
        holder.addComponent(TransformComponent.getComponentType(), new TransformComponent(position, rotation));
        holder.addComponent(HeadRotation.getComponentType(), new HeadRotation(rotation));
        holder.addComponent(ModelComponent.getComponentType(), new ModelComponent(model));
        holder.addComponent(PersistentModel.getComponentType(), new PersistentModel(model.toReference()));
        holder.addComponent(BoundingBox.getComponentType(), new BoundingBox(model.getBoundingBox()));
        holder.addComponent(NetworkId.getComponentType(), new NetworkId(buffer.getExternalData().takeNextNetworkId()));
        holder.ensureComponent(EntityModule.get().getVisibleComponentType());
        holder.ensureComponent(EntityStore.REGISTRY.getNonSerializedComponentType());
        holder.ensureComponent(ProjectilePassthrough.getComponentType());
        var time = buffer.getResource(TimeResource.getResourceType());
        holder.addComponent(DespawnComponent.getComponentType(), DespawnComponent.despawnInSeconds(
                time, LIFETIME_SECONDS));
        holder.addComponent(ChargedMeteorPlugin.contactType,
                new MeteorContact(time.getNow().plusMillis(MeteorContact.FALL_MILLISECONDS)));

        // Reuse Hytale's ability proxy to start the fall effects and retain caster ownership.
        holder.addComponent(AbilityEntityRepeat.getComponentType(),
                new AbilityEntityRepeat(caster, new String[]{FALL_ROOT}, new float[]{10f}));
        holder.addComponent(InteractionModule.get().getInteractionManagerComponent(),
                new InteractionManager(null, new InteractionSimulationHandler()));
        var modifiers = ImpactModifiers.resolve(context, caster, buffer);
        if (modifiers != null) {
            holder.addComponent(ImpactModifiers.getComponentType(), new ImpactModifiers(
                    modifiers.getAttributes(), modifiers.getOnHitEffectIds(), modifiers.getElementalCauseId()));
        }
        buffer.addEntity(holder, AddReason.SPAWN);
        MeteorLighting.spawn(buffer, ChargedMeteorPlugin.lightingType, position);
    }

    private static Vector3d resolveImpact(Ref<EntityStore> caster, CommandBuffer<EntityStore> buffer) {
        var look = TargetUtil.getLook(caster, buffer);
        if (look == null) {
            return null;
        }
        var origin = look.getPosition();
        var direction = new Vector3d(look.getDirection()).normalize();
        var blockHit = TargetUtil.getTargetLocation(caster, AIM_RANGE, buffer);
        var nearest = blockHit == null ? AIM_RANGE : origin.distance(blockHit);
        Vector3d creaturePosition = null;
        for (var target : TargetUtil.getAllEntitiesInSphere(origin, AIM_RANGE, buffer)) {
            if (caster.equals(target) || !LivingTargetInteraction.canHitCreature(target, buffer)) {
                continue;
            }
            var transform = buffer.getComponent(target, TransformComponent.getComponentType());
            var hitbox = buffer.getComponent(target, BoundingBox.getComponentType());
            if (transform == null || hitbox == null) {
                continue;
            }
            var feet = transform.getPosition();
            double distance = CollisionMath.intersectRayAABB(
                    origin, direction, feet.x, feet.y, feet.z, hitbox.getBoundingBox());
            if (distance >= 0 && distance < nearest) {
                nearest = distance;
                creaturePosition = feet;
            }
        }

        if (creaturePosition != null) {
            // Snapshot the creature's feet now so the telegraph and strike share a fixed point.
            return new Vector3d(creaturePosition);
        }
        return blockHit == null ? new Vector3d(origin).fma(AIM_RANGE, direction) : blockHit;
    }
}
