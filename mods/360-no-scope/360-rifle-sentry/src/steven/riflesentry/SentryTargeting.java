package steven.riflesentry;

import com.airijko.endlessleveling.EndlessLeveling;
import com.airijko.endlessleveling.ecs.components.SummonOwnerComponent;
import com.hypixel.hytale.builtin.deployables.DeployablesUtils;
import com.hypixel.hytale.builtin.deployables.component.DeployableComponent;
import com.hypixel.hytale.builtin.deployables.component.DeployableComponent.DeployableFlag;
import com.hypixel.hytale.builtin.deployables.component.DeployableProjectileComponent;
import com.hypixel.hytale.builtin.deployables.component.DeployableProjectileShooterComponent;
import com.hypixel.hytale.builtin.deployables.config.DeployableTurretConfig;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.math.shape.Box;
import com.hypixel.hytale.math.util.MathUtil;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.math.vector.Vector3dUtil;
import com.hypixel.hytale.protocol.BlockMaterial;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.asset.type.blocktype.config.BlockType;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.group.EntityGroup;
import com.hypixel.hytale.server.core.modules.entity.component.BoundingBox;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.modules.projectile.config.StandardPhysicsProvider;
import com.hypixel.hytale.server.core.modules.time.TimeResource;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.TargetUtil;
import com.hypixel.hytale.server.npc.blackboard.Blackboard;
import com.hypixel.hytale.server.npc.blackboard.view.attitude.AttitudeView;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;
import com.ziggfreed.mmoskilltree.ability.effect.MmoSummonComponent;
import java.lang.ref.WeakReference;
import java.time.Instant;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import org.joml.Vector3d;

/** Uses the native deployment and projectile physics with a hostile-only firing policy. */
public final class SentryTargeting extends DeployableTurretConfig {
    public static final BuilderCodec<SentryTargeting> CODEC = BuilderCodec.builder(
        SentryTargeting.class, SentryTargeting::new, DeployableTurretConfig.CODEC).build();

    private static final int ATTACK_STATE = 3;
    private static final double MUZZLE_DISTANCE = 2.0;
    private static final double MIN_ALIGNMENT = Math.cos(Math.toRadians(2));
    private static final double MAX_TARGET_SPEED = 15;
    private static final double MIN_TRACKING_SPEED_SQUARED = 0.05 * 0.05;
    private static final long OWNER_MARK_SECONDS = 5;
    private static final float IDLE_SWEEP_TIME = 6f;
    private static final double IDLE_SWEEP_ANGLE = Math.toRadians(45);
    private static final float YAW_RADIANS_PER_SECOND = (float) Math.toRadians(180);
    private static final float PITCH_RADIANS_PER_SECOND = (float) Math.toRadians(105);
    private static final float MAX_ROTATION_STEP_SECONDS = 0.1f;
    private static final Map<Ref<EntityStore>, TargetMark> OWNER_MARKS =
        Collections.synchronizedMap(new WeakHashMap<>());
    private final Map<Ref<EntityStore>, TrackSample> tracked = Collections.synchronizedMap(new WeakHashMap<>());
    private final Map<Ref<EntityStore>, Float> idleSweepTime = Collections.synchronizedMap(new WeakHashMap<>());

    /** Level the native holder before its transform can reach entity tracking. */
    static final class LevelFloorSpawn extends HolderSystem<EntityStore> {
        @Override
        public Query<EntityStore> getQuery() {
            return Query.and(DeployableComponent.getComponentType(), TransformComponent.getComponentType(),
                HeadRotation.getComponentType());
        }

        @Override
        public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
            var deployable = holder.getComponent(DeployableComponent.getComponentType());
            if (!RifleSentryPlugin.isRifleSentry(deployable) || !"UP".equals(deployable.getSpawnFace())) {
                return;
            }
            // MMOSkillTree passes the owner's look, including pitch and roll, as the deployable orientation.
            var transform = holder.getComponent(TransformComponent.getComponentType());
            Rotation3f level = new Rotation3f(0, transform.getRotation().yaw(), 0);
            transform.setRotation(level);
            holder.getComponent(HeadRotation.getComponentType()).setRotation(level);
        }

        @Override
        public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {}
    }

    @Override
    public void tick(DeployableComponent deployable, float dt, int index, ArchetypeChunk<EntityStore> chunk,
                     Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        if (deployable.getFlag(DeployableFlag.STATE) != ATTACK_STATE) {
            super.tick(deployable, dt, index, chunk, store, buffer);
            return;
        }

        Ref<EntityStore> turret = chunk.getReferenceTo(index);
        var shooter = store.getComponent(turret, DeployableProjectileShooterComponent.getComponentType());
        var transform = store.getComponent(turret, TransformComponent.getComponentType());
        var head = store.getComponent(turret, HeadRotation.getComponentType());
        if (shooter == null || transform == null || head == null) {
            return;
        }
        resolveProjectiles(turret, deployable, shooter, buffer);
        deployable.incrementTimeSinceLastAttack(dt);

        Vector3d pivot = new Vector3d(transform.getPosition());
        Vector3d offset = projectileSpawnOffsets.get(deployable.getSpawnFace());
        if (offset != null) {
            pivot.add(offset);
        }
        LineOfFire aim = findAim(turret, deployable, shooter.getActiveTarget(), pivot, tracked.get(turret), dt, buffer);
        shooter.setActiveTarget(aim == null || !aim.clear() ? null : aim.target());
        float turnTime = Float.isFinite(dt) ? MathUtil.clamp(dt, 0, MAX_ROTATION_STEP_SECONDS) : 0;
        if (aim == null) {
            tracked.remove(turret);
            if ("UP".equals(deployable.getSpawnFace())) {
                float phase = idleSweepTime.merge(turret, turnTime, (elapsed, step) -> (elapsed + step) % IDLE_SWEEP_TIME);
                double sweep = IDLE_SWEEP_ANGLE * Math.sin(phase * (2 * Math.PI / IDLE_SWEEP_TIME));
                Rotation3f scan = new Rotation3f(0, transform.getRotation().yaw() + (float) sweep, 0);
                turnHead(head, scan, turnTime);
            }
            SentrySensorFeedback.update(turret, transform, head, SentrySensorFeedback.State.IDLE, dt, buffer);
            return;
        }

        idleSweepTime.remove(turret);
        tracked.put(turret, new TrackSample(new WeakReference<>(aim.target()), aim.center()));
        Vector3d direction = new Vector3d(aim.intercept()).sub(pivot);
        double distance = direction.length();
        if (!(distance > 0.2) || !Double.isFinite(distance)) {
            SentrySensorFeedback.update(turret, transform, head, SentrySensorFeedback.State.BLOCKED, dt, buffer);
            return;
        }
        direction.div(distance);
        Rotation3f tracking = turnHead(head, Rotation3f.lookAt(direction), turnTime);
        Vector3d bore = Vector3dUtil.setYawPitch(tracking.yaw(), tracking.pitch(), new Vector3d());
        float cooldown = deployable.getFlag(DeployableFlag.BURST_SHOTS) < burstCount ? shotInterval : burstCooldown;
        boolean aligned = bore.dot(direction) >= MIN_ALIGNMENT;
        SentrySensorFeedback.State state = !aim.clear() ? SentrySensorFeedback.State.BLOCKED
            : aligned ? SentrySensorFeedback.State.LOCKED : SentrySensorFeedback.State.TRACKING;
        SentrySensorFeedback.update(turret, transform, head, state, dt, buffer);
        if (!aim.clear() || !aligned || deployable.getTimeSinceLastAttack() < cooldown) {
            return;
        }

        // The shot uses the exact intercept whose path was checked. Leave the visible head's turn rate intact.
        Vector3d origin = new Vector3d(pivot).fma(Math.min(MUZZLE_DISTANCE, distance * 0.45), direction);
        shooter.spawnProjectile(turret, buffer, projectileConfig, origin, direction);
        playAnimation(store, turret, this, "Shoot");
        deployable.setFlag(DeployableFlag.BURST_SHOTS, 1);
        deployable.setTimeSinceLastAttack(0);
    }

    private static Rotation3f turnHead(HeadRotation head, Rotation3f desired, float turnTime) {
        Rotation3f current = head.getRotation();
        float yawLimit = YAW_RADIANS_PER_SECOND * turnTime;
        float pitchLimit = PITCH_RADIANS_PER_SECOND * turnTime;
        float yawDelta = MathUtil.shortAngleDistance(current.yaw(), desired.yaw());
        float yaw = MathUtil.wrapAngle(current.yaw() + MathUtil.clamp(yawDelta, -yawLimit, yawLimit));
        float pitch = current.pitch() + MathUtil.clamp(desired.pitch() - current.pitch(), -pitchLimit, pitchLimit);
        Rotation3f rotation = new Rotation3f(pitch, yaw, 0);
        head.setRotation(rotation);
        return rotation;
    }

    private LineOfFire findAim(Ref<EntityStore> turret, DeployableComponent deployable, Ref<EntityStore> current,
                               Vector3d pivot, TrackSample previous, float dt, ComponentAccessor<EntityStore> accessor) {
        double farthest = Math.max(detectionRadius, trackableRadius);
        double speed = projectileConfig.getLaunchForce();
        double leadRange = speed > 0 ? farthest * MAX_TARGET_SPEED / speed : 0;
        List<Ref<EntityStore>> nearby = TargetUtil.getAllEntitiesInSphere(pivot, farthest + leadRange + 2, accessor);
        Ref<EntityStore> marked = markedTarget(deployable.getOwner(), accessor);
        LineOfFire mark = evaluateAim(turret, deployable, marked, pivot,
            marked == current ? trackableRadius : detectionRadius, previous, dt, nearby, accessor);
        if (mark != null && mark.clear()) {
            return mark;
        }
        LineOfFire active = current == marked ? mark : evaluateAim(turret, deployable, current, pivot,
            trackableRadius, previous, dt, nearby, accessor);
        if (active != null && active.clear()) {
            return active;
        }

        LineOfFire blocked = mark != null ? mark : active;
        boolean hasPreferredBlocked = blocked != null;
        LineOfFire closestClear = null;
        double closestClearDistance = detectionRadius;
        for (Ref<EntityStore> candidate : nearby) {
            if (candidate == marked || candidate == current) {
                continue;
            }
            LineOfFire tested = evaluateAim(turret, deployable, candidate, pivot, closestClearDistance,
                previous, dt, nearby, accessor);
            if (tested == null) {
                continue;
            }
            double distance = tested.center().distance(pivot);
            if (tested.clear()) {
                closestClear = tested;
                closestClearDistance = distance;
            } else if (!hasPreferredBlocked && (blocked == null || distance < blocked.center().distance(pivot))) {
                blocked = tested;
            }
        }
        return closestClear != null ? closestClear : blocked;
    }

    private LineOfFire evaluateAim(Ref<EntityStore> turret, DeployableComponent deployable, Ref<EntityStore> target,
                                   Vector3d pivot, double maxDistance, TrackSample previous, float dt,
                                   List<Ref<EntityStore>> nearby, ComponentAccessor<EntityStore> accessor) {
        if (!isHostile(turret, deployable, target, accessor)) {
            return null;
        }
        var transform = accessor.getComponent(target, TransformComponent.getComponentType());
        var bounds = accessor.getComponent(target, BoundingBox.getComponentType());
        if (transform == null || bounds == null) {
            return null;
        }
        Box box = bounds.getBoundingBox();
        Vector3d center = new Vector3d(box.min).add(box.max).mul(0.5).add(transform.getPosition());
        double distanceSquared = center.distanceSquared(pivot);
        if (!(distanceSquared > 0.04 && distanceSquared <= maxDistance * maxDistance)) {
            return null;
        }
        Vector3d intercept = interceptPoint(target, center, pivot, previous, dt, accessor);
        boolean clear = blockLineClear(pivot, center, accessor)
            && (intercept.equals(center) || blockLineClear(pivot, intercept, accessor))
            && !friendlyInLine(turret, deployable, target, pivot, intercept, nearby, accessor);
        return new LineOfFire(target, center, intercept, clear);
    }

    private Vector3d interceptPoint(Ref<EntityStore> target, Vector3d center, Vector3d pivot, TrackSample previous, float dt,
                                    ComponentAccessor<EntityStore> accessor) {
        if (!(projectileConfig.getLaunchForce() > 0)) {
            return center;
        }
        var velocity = accessor.getComponent(target, Velocity.getComponentType());
        Vector3d movement = velocity == null ? new Vector3d() : new Vector3d(velocity.getVelocity());
        if (!movement.isFinite() || movement.lengthSquared() < MIN_TRACKING_SPEED_SQUARED) {
            // Walking NPCs can steer their transforms without a populated physics velocity.
            if (previous == null || previous.target().get() != target || dt <= 0 || dt > 0.2f) {
                return center;
            }
            movement.set(center).sub(previous.center()).div(dt);
            if (!movement.isFinite() || movement.lengthSquared() > MAX_TARGET_SPEED * MAX_TARGET_SPEED) {
                return center; // Ignore teleports and abrupt position corrections.
            }
        } else if (movement.lengthSquared() > MAX_TARGET_SPEED * MAX_TARGET_SPEED) {
            movement.normalize(MAX_TARGET_SPEED);
        }
        double distance = center.distance(pivot);
        double flightTime = (distance - Math.min(MUZZLE_DISTANCE, distance * 0.45)) / projectileConfig.getLaunchForce();
        return new Vector3d(center).fma(flightTime, movement);
    }

    private boolean blockLineClear(Vector3d from, Vector3d to, ComponentAccessor<EntityStore> accessor) {
        if (!doLineOfSightTest) {
            return true;
        }
        Vector3d ray = new Vector3d(to).sub(from);
        double distance = ray.length();
        if (!(distance > 0) || !Double.isFinite(distance)) {
            return false;
        }
        ray.div(distance);
        return TargetUtil.getTargetBlock(accessor.getExternalData().getWorld().getChunkStore(),
            (id, rotation) -> {
                BlockType block = BlockType.getAssetMap().getAsset(id);
                return block != null && block.getMaterial() == BlockMaterial.Solid;
            }, from.x, from.y, from.z, ray.x, ray.y, ray.z, distance) == null;
    }

    private static boolean friendlyInLine(Ref<EntityStore> turret, DeployableComponent deployable, Ref<EntityStore> target,
                                          Vector3d from, Vector3d to, List<Ref<EntityStore>> nearby,
                                          ComponentAccessor<EntityStore> accessor) {
        for (Ref<EntityStore> other : nearby) {
            if (other == turret || other == target || other == null || !other.isValid()) {
                continue;
            }
            var bounds = accessor.getComponent(other, BoundingBox.getComponentType());
            var transform = accessor.getComponent(other, TransformComponent.getComponentType());
            if (bounds != null && transform != null
                && new Box(bounds.getBoundingBox()).offset(transform.getPosition()).intersectsLine(from, to)
                && !isHostile(turret, deployable, other, accessor)) {
                return true;
            }
        }
        return false;
    }

    private void resolveProjectiles(Ref<EntityStore> turret, DeployableComponent deployable,
                                    DeployableProjectileShooterComponent shooter, CommandBuffer<EntityStore> buffer) {
        Iterator<Ref<EntityStore>> shots = shooter.getProjectiles().iterator();
        while (shots.hasNext()) {
            Ref<EntityStore> shot = shots.next();
            if (shot == null || !shot.isValid()) {
                shots.remove();
                continue;
            }
            var projectile = buffer.getComponent(shot, DeployableProjectileComponent.getComponentType());
            var physics = buffer.getComponent(shot, StandardPhysicsProvider.getComponentType());
            Ref<EntityStore> hit = projectile == null ? null : projectile.takeHitEntityRef();
            if (hit != null && isHostile(turret, deployable, hit, buffer)) {
                int cause = DamageCause.getAssetMap().getIndex("Physical");
                Damage damage = new Damage(new Damage.EntitySource(turret), cause, projectileDamage);
                var impact = buffer.getComponent(shot, TransformComponent.getComponentType());
                SentryThirdHit.markProjectile(damage, impact == null ? null : impact.getPosition());
                DamageSystems.executeDamage(hit, buffer, damage);
                if (impact != null) {
                    DeployablesUtils.playSoundEventsAtEntity(hit, buffer, projectileHitLocalSoundEventIndex,
                        projectileHitWorldSoundEventIndex, impact.getPosition());
                }
            }
            if (hit != null || projectile == null || physics == null
                || physics.getState() != StandardPhysicsProvider.STATE.ACTIVE) {
                shots.remove();
                buffer.removeEntity(shot, RemoveReason.REMOVE);
            }
        }
    }

    private static boolean isHostile(Ref<EntityStore> turret, DeployableComponent deployable, Ref<EntityStore> target,
                                     ComponentAccessor<EntityStore> accessor) {
        return target != turret && isHostileTo(deployable.getOwner(), target, accessor);
    }

    private static boolean isHostileTo(Ref<EntityStore> owner, Ref<EntityStore> target,
                                       ComponentAccessor<EntityStore> accessor) {
        if (target == null || !target.isValid() || target == owner
            || owner == null || !owner.isValid() || owner.getStore() != target.getStore()
            || accessor.getComponent(target, NPCEntity.getComponentType()) == null
            || accessor.getComponent(target, Player.getComponentType()) != null
            || accessor.getComponent(target, PlayerRef.getComponentType()) != null
            || accessor.getComponent(target, DeathComponent.getComponentType()) != null
            || accessor.getComponent(target, DeployableComponent.getComponentType()) != null) {
            return false;
        }
        var stats = accessor.getComponent(target, EntityStatMap.getComponentType());
        var health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || !(health.get() > 0) || isSummon(target, accessor)) {
            return false;
        }
        var group = accessor.getComponent(owner, EntityGroup.getComponentType());
        if (group != null && group.isMember(target)) {
            return false;
        }
        WorldSupport worldSupport = WorldSupport.get(target, accessor);
        if (worldSupport == null) {
            return false;
        }
        Blackboard blackboard = accessor.getResource(Blackboard.getResourceType());
        var view = blackboard.getView(AttitudeView.class, target, accessor);
        var npc = accessor.getComponent(target, NPCEntity.getComponentType());
        return view != null && view.getAttitude(target, npc.getRoleIndex(), owner, accessor) == Attitude.HOSTILE;
    }

    private static boolean isSummon(Ref<EntityStore> target, ComponentAccessor<EntityStore> accessor) {
        var endlessType = SummonOwnerComponent.getComponentType();
        var mmoType = MmoSummonComponent.getComponentType();
        if (endlessType != null && accessor.getComponent(target, endlessType) != null
            || mmoType != null && accessor.getComponent(target, mmoType) != null) {
            return true;
        }
        var leveling = EndlessLeveling.getInstance();
        var registry = leveling == null ? null : leveling.getSummonOwnerRegistry();
        var id = accessor.getComponent(target, UUIDComponent.getComponentType());
        return registry != null && id != null && registry.isSummon(id.getUuid());
    }

    private static Ref<EntityStore> markedTarget(Ref<EntityStore> owner, ComponentAccessor<EntityStore> accessor) {
        TargetMark mark = OWNER_MARKS.get(owner);
        if (mark == null) {
            return null;
        }
        Ref<EntityStore> target = mark.target().get();
        Instant now = accessor.getResource(TimeResource.getResourceType()).getNow();
        if (target == null || !target.isValid() || !now.isBefore(mark.expires())) {
            OWNER_MARKS.remove(owner, mark);
            return null;
        }
        return target;
    }

    private record LineOfFire(Ref<EntityStore> target, Vector3d center, Vector3d intercept, boolean clear) {}
    private record TrackSample(WeakReference<Ref<EntityStore>> target, Vector3d center) {}
    private record TargetMark(WeakReference<Ref<EntityStore>> target, Instant expires) {}

    static final class OwnerHitMark extends DamageEventSystem {
        @Override
        public Query<EntityStore> getQuery() {
            return NPCEntity.getComponentType();
        }

        @Override
        public SystemGroup<EntityStore> getGroup() {
            return DamageModule.get().getInspectDamageGroup();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, Damage damage) {
            if (damage.isCancelled() || !(damage.getAmount() > 0) || !Float.isFinite(damage.getAmount())
                || Boolean.TRUE.equals(damage.getIfPresentMetaObject(Damage.BLOCKED))
                || !(damage.getSource() instanceof Damage.EntitySource source)) {
                return;
            }
            InteractionType interaction = damage.getIfPresentMetaObject(Damage.INTERACTION_TYPE);
            boolean weaponHit = source.getClass() == Damage.ProjectileSource.class
                ? interaction == InteractionType.ProjectileHit
                : source.getClass() == Damage.EntitySource.class
                    && (interaction == InteractionType.Primary || interaction == InteractionType.Secondary);
            if (!weaponHit || !RifleSentryPlugin.usable(source.getRef(), store)) {
                return;
            }
            Ref<EntityStore> playerRef = source.getRef();
            PlayerRef player = buffer.getComponent(playerRef, PlayerRef.getComponentType());
            Ref<EntityStore> target = chunk.getReferenceTo(index);
            if (player == null || !player.isValid() || player.getReference() != playerRef
                || !isHostileTo(playerRef, target, buffer)) {
                return;
            }
            Instant expires = buffer.getResource(TimeResource.getResourceType()).getNow().plusSeconds(OWNER_MARK_SECONDS);
            OWNER_MARKS.put(playerRef, new TargetMark(new WeakReference<>(target), expires));
        }
    }

    public static final class DamageGuard extends DamageEventSystem {
        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public SystemGroup<EntityStore> getGroup() {
            return DamageModule.get().getGatherDamageGroup();
        }

        @Override
        public Set<Dependency<EntityStore>> getDependencies() {
            return Set.of(new SystemDependency<>(Order.BEFORE, RifleSentryPlugin.ScaleOwnerDamage.class));
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, Damage damage) {
            Ref<EntityStore> turret = RifleSentryPlugin.rifleSource(damage, store, buffer);
            if (turret != null && !isHostile(turret, buffer.getComponent(turret, DeployableComponent.getComponentType()),
                chunk.getReferenceTo(index), buffer)) {
                damage.setCancelled(true);
            }
        }
    }
}
