package steven.riflesentry;

import com.hypixel.hytale.builtin.deployables.component.DeployableComponent;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.spatial.SpatialResource;
import com.hypixel.hytale.math.vector.Vector3dUtil;
import com.hypixel.hytale.server.core.modules.entity.EntityModule;
import com.hypixel.hytale.server.core.modules.entity.component.HeadRotation;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import org.joml.Vector3d;

/** Sends short, nearby sensor pulses as the sentry tracks and lines up a shot. */
final class SentrySensorFeedback {
    private static final double VIEW_RADIUS = 24;
    private static final float REFRESH_SECONDS = 0.28f;
    private static final float TRANSITION_SECONDS = 0.12f;
    private static final double MODEL_PIXELS_PER_BLOCK = 32;
    private static final double HEAD_HEIGHT = 33;
    private static final double WINDOW_HEIGHT = 7.3;
    private static final double WINDOW_FORWARD = 5.15;
    private static final Map<Ref<EntityStore>, Pulse> PULSES = new WeakHashMap<>();

    enum State {
        IDLE(null),
        TRACKING("AS_Rifle_Sentry_Sensor_Tracking"),
        LOCKED("AS_Rifle_Sentry_Sensor_Locked"),
        BLOCKED("AS_Rifle_Sentry_Sensor_Blocked");

        private final String particle;

        State(String particle) {
            this.particle = particle;
        }
    }

    private SentrySensorFeedback() {}

    static void update(Ref<EntityStore> turret, TransformComponent transform, HeadRotation head, State state,
                       float dt, CommandBuffer<EntityStore> buffer) {
        if (!Float.isFinite(dt) || dt <= 0) {
            return;
        }
        synchronized (PULSES) {
            Pulse pulse = PULSES.computeIfAbsent(turret, unused -> new Pulse());
            if (!pulse.advance(state, dt)) {
                return;
            }
        }
        var deployable = buffer.getComponent(turret, DeployableComponent.getComponentType());
        if (deployable == null || !"UP".equals(deployable.getSpawnFace())) {
            return;
        }
        double unit = deployable.getConfig().getModel().getScale() / MODEL_PIXELS_PER_BLOCK;
        var rotation = head.getRotation();
        var direction = Vector3dUtil.setYawPitch(rotation.yaw(), rotation.pitch(), new Vector3d());
        var up = rotation.transform(new Vector3d(0, unit * WINDOW_HEIGHT, 0));
        var sensor = new Vector3d(transform.getPosition()).add(0, unit * HEAD_HEIGHT, 0)
            .add(up).fma(unit * WINDOW_FORWARD, direction);
        if (sensor.isFinite()) {
            buffer.run(actual -> emit(state.particle, sensor, actual));
        }
    }

    private static void emit(String particle, Vector3d sensor, Store<EntityStore> store) {
        var spatial = store.getResource(EntityModule.get().getPlayerSpatialResourceType());
        List<Ref<EntityStore>> viewers = SpatialResource.getThreadLocalReferenceList();
        spatial.getSpatialStructure().collect(sensor, VIEW_RADIUS, viewers);
        if (!viewers.isEmpty()) {
            ParticleUtil.spawnParticleEffect(particle, sensor, viewers, store);
        }
    }

    private static final class Pulse {
        private State emittedState;
        private float elapsed = REFRESH_SECONDS;

        boolean advance(State next, float dt) {
            elapsed = Math.min(REFRESH_SECONDS, elapsed + dt);
            if (next == State.IDLE) {
                emittedState = next;
                return false;
            }
            float interval = emittedState == next ? REFRESH_SECONDS : TRANSITION_SECONDS;
            if (elapsed < interval) {
                return false;
            }
            emittedState = next;
            elapsed = 0;
            return true;
        }
    }
}
