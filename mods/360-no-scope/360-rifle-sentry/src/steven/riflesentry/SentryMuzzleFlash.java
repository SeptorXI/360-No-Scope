package steven.riflesentry;

import com.hypixel.hytale.builtin.deployables.component.DeployableComponent;
import com.hypixel.hytale.builtin.deployables.component.DeployableProjectileComponent;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.RefChangeSystem;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.projectile.config.StandardPhysicsProvider;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3d;

/** Emits the sentry's world-space muzzle effect when an actual projectile launches. */
final class SentryMuzzleFlash extends RefChangeSystem<EntityStore, DeployableProjectileComponent> {
    private static final String EFFECT = "AS_Rifle_Sentry_PlasmaFlash";
    private static final double HEAD_HEIGHT = 33.0 / 32.0;
    private static final double BARREL_LENGTH = 32.0 / 32.0;

    @Override
    public ComponentType<EntityStore, DeployableProjectileComponent> componentType() {
        return DeployableProjectileComponent.getComponentType();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Query.and(StandardPhysicsProvider.getComponentType(), TransformComponent.getComponentType());
    }

    @Override
    public void onComponentAdded(Ref<EntityStore> projectile, DeployableProjectileComponent component,
                                 Store<EntityStore> store, CommandBuffer<EntityStore> commands) {
        var physics = store.getComponent(projectile, StandardPhysicsProvider.getComponentType());
        var creator = physics.getCreatorUuid();
        if (creator == null) {
            return;
        }
        var sentry = store.getExternalData().getRefFromUUID(creator);
        if (!RifleSentryPlugin.usable(sentry, store)) {
            return;
        }
        var deployable = store.getComponent(sentry, DeployableComponent.getComponentType());
        if (!RifleSentryPlugin.isRifleSentry(deployable) || !"UP".equals(deployable.getSpawnFace())) {
            return;
        }
        var support = store.getComponent(sentry, TransformComponent.getComponentType());
        var launch = store.getComponent(projectile, TransformComponent.getComponentType());
        if (support == null || launch == null) {
            return;
        }
        float scale = deployable.getConfig().getModel().getScale();
        var pivot = new Vector3d(support.getPosition()).add(0, scale * HEAD_HEIGHT, 0);
        // The native launch starts partway along the bore. Its position identifies the shot axis.
        var forward = new Vector3d(launch.getPosition()).sub(pivot);
        if (!forward.isFinite() || forward.lengthSquared() < 1.0e-6) {
            return;
        }
        var muzzle = forward.normalize(scale * BARREL_LENGTH).add(pivot);
        float yaw = launch.getRotation().yaw();
        float pitch = launch.getRotation().pitch();
        commands.run(actual -> ParticleUtil.spawnParticleEffect(EFFECT, muzzle, yaw, pitch, 0, 1, 0, actual));
    }

    @Override
    public void onComponentSet(Ref<EntityStore> projectile, DeployableProjectileComponent previous,
                               DeployableProjectileComponent current, Store<EntityStore> store,
                               CommandBuffer<EntityStore> commands) {}

    @Override
    public void onComponentRemoved(Ref<EntityStore> projectile, DeployableProjectileComponent component,
                                   Store<EntityStore> store, CommandBuffer<EntityStore> commands) {}
}
