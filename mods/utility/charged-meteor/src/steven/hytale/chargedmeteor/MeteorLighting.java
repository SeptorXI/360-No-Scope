package steven.hytale.chargedmeteor;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.logger.HytaleLogger;
import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.server.core.modules.entity.DespawnComponent;
import com.hypixel.hytale.server.core.modules.entity.EntityModule;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.modules.entity.component.ProjectilePassthrough;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.tracker.NetworkId;
import com.hypixel.hytale.server.core.modules.time.TimeResource;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.bson.BsonDocument;
import org.joml.Vector3d;

record MeteorLighting(Vector3d impact, Instant launchedAt) implements Component<EntityStore> {
    private static final String FALL_CLIP = "/Common/Items/Abilities/ChargedMeteor/ChargedMeteor_Fall.blockyanim";
    private static final long GROUND_GLOW_MILLISECONDS = 300;
    private static final long CONTACT_GLOW_MILLISECONDS = 650;
    private static final double FRAMES_PER_MILLISECOND = 0.06;
    private static final double MODEL_UNITS_PER_BLOCK = 32;
    private static final double GROUND_LIGHT_HEIGHT = 0.8;
    private static final ColorLight GROUND_GLOW = color(12, 15, 2, 1);
    private static final ColorLight FALL_GLOW = color(15, 15, 7, 2);
    private static final List<PositionKey> FALL_TRACK = loadFallTrack();

    @Override
    public MeteorLighting clone() {
        return new MeteorLighting(new Vector3d(impact), launchedAt);
    }

    static void spawn(CommandBuffer<EntityStore> buffer, ComponentType<EntityStore, MeteorLighting> type,
                      Vector3d impact) {
        var chunks = buffer.getExternalData().getWorld().getChunkStore();
        var lightPosition = groundPosition(chunks, impact);
        if (lightPosition == null) {
            return;
        }
        var time = buffer.getResource(TimeResource.getResourceType());
        var holder = EntityStore.REGISTRY.newHolder();
        holder.addComponent(TransformComponent.getComponentType(), new TransformComponent(lightPosition, new Rotation3f()));
        holder.addComponent(DynamicLight.getComponentType(), new DynamicLight(GROUND_GLOW));
        holder.addComponent(NetworkId.getComponentType(), new NetworkId(buffer.getExternalData().takeNextNetworkId()));
        holder.ensureComponent(EntityModule.get().getVisibleComponentType());
        holder.ensureComponent(ProjectilePassthrough.getComponentType());
        holder.ensureComponent(EntityStore.REGISTRY.getNonSerializedComponentType());
        holder.addComponent(DespawnComponent.getComponentType(), DespawnComponent.despawnInMilliseconds(
                time, MeteorContact.FALL_MILLISECONDS + CONTACT_GLOW_MILLISECONDS));
        holder.addComponent(type, new MeteorLighting(new Vector3d(impact), time.getNow()));
        buffer.addEntity(holder, AddReason.SPAWN);
    }

    private static Vector3d groundPosition(ChunkStore chunks, Vector3d impact) {
        var raised = new Vector3d(impact).add(0, GROUND_LIGHT_HEIGHT, 0);
        if (isSectionTicking(chunks, raised)) {
            return raised;
        }
        return isSectionTicking(chunks, impact) ? impact : null;
    }

    private static boolean isSectionTicking(ChunkStore chunks, Vector3d position) {
        var section = chunks.getChunkSectionReference(ChunkUtil.chunkCoordinate(position.x),
                ChunkUtil.chunkCoordinate(position.y), ChunkUtil.chunkCoordinate(position.z));
        return section != null && section.isValid()
                && !chunks.getStore().getArchetype(section).contains(ChunkStore.REGISTRY.getNonTickingComponentType());
    }

    private static ColorLight color(int radius, int red, int green, int blue) {
        return new ColorLight((byte) radius, (byte) red, (byte) green, (byte) blue);
    }

    private static List<PositionKey> loadFallTrack() {
        try (var input = MeteorLighting.class.getResourceAsStream(FALL_CLIP)) {
            if (input == null) {
                throw new IOException("Missing bundled meteor animation");
            }
            var clip = BsonDocument.parse(new String(input.readAllBytes(), StandardCharsets.UTF_8));
            var keys = clip.getDocument("nodeAnimations").getDocument("MeteorBody").getArray("position");
            var track = new ArrayList<PositionKey>(keys.size());
            for (var key : keys) {
                var frame = key.asDocument();
                var position = frame.getDocument("delta");
                track.add(new PositionKey(frame.getNumber("time").doubleValue(),
                        position.getNumber("x").doubleValue(), position.getNumber("y").doubleValue(),
                        position.getNumber("z").doubleValue()));
            }
            if (track.size() < 2) {
                throw new IOException("MeteorBody animation needs at least two position keys");
            }
            return List.copyOf(track);
        } catch (IOException | RuntimeException e) {
            HytaleLogger.forEnclosingClass().atWarning().withCause(e).log("Using fallback meteor light animation");
            return List.of(new PositionKey(0, 0, 1300, 0), new PositionKey(54, 2, 697, 2),
                    new PositionKey(106, 2, 668, 10), new PositionKey(174, 4, 389, 3),
                    new PositionKey(197, 0, 175, 0));
        }
    }

    private Vector3d fallPosition(double frame) {
        var previous = FALL_TRACK.getFirst();
        for (int index = 1; index < FALL_TRACK.size(); index++) {
            var next = FALL_TRACK.get(index);
            if (frame <= next.frame()) {
                double fraction = Math.clamp((frame - previous.frame()) / (next.frame() - previous.frame()), 0, 1);
                return new Vector3d(previous.x(), previous.y(), previous.z())
                        .lerp(new Vector3d(next.x(), next.y(), next.z()), fraction)
                        .div(MODEL_UNITS_PER_BLOCK).add(impact);
            }
            previous = next;
        }
        return new Vector3d(previous.x(), previous.y(), previous.z()).div(MODEL_UNITS_PER_BLOCK).add(impact);
    }

    private record PositionKey(double frame, double x, double y, double z) {}

    static final class LightingSystem extends EntityTickingSystem<EntityStore> {
        private final ComponentType<EntityStore, MeteorLighting> lightingType;

        LightingSystem(ComponentType<EntityStore, MeteorLighting> lightingType) {
            this.lightingType = lightingType;
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.and(lightingType, TransformComponent.getComponentType(), DynamicLight.getComponentType());
        }

        @Override
        public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                         CommandBuffer<EntityStore> buffer) {
            var lighting = chunk.getComponent(index, lightingType);
            var now = buffer.getResource(TimeResource.getResourceType()).getNow();
            long elapsed = Duration.between(lighting.launchedAt(), now).toMillis();
            if (elapsed < GROUND_GLOW_MILLISECONDS) {
                return;
            }

            var transform = chunk.getComponent(index, TransformComponent.getComponentType());
            var light = chunk.getComponent(index, DynamicLight.getComponentType());
            var chunks = store.getExternalData().getWorld().getChunkStore();
            ColorLight glow;
            if (elapsed < MeteorContact.FALL_MILLISECONDS) {
                var position = lighting.fallPosition(elapsed * FRAMES_PER_MILLISECOND);
                position.y = Math.max(position.y, lighting.impact().y + GROUND_LIGHT_HEIGHT);
                // The engine unloads non-player entities entering an inactive section.
                if (isSectionTicking(chunks, position)) {
                    transform.setPosition(position);
                }
                glow = FALL_GLOW;
            } else {
                var position = groundPosition(chunks, lighting.impact());
                if (position != null && !transform.getPosition().equals(position)) {
                    transform.setPosition(position);
                }
                double remaining = Math.max(0, 1 - (elapsed - MeteorContact.FALL_MILLISECONDS)
                        / (double) CONTACT_GLOW_MILLISECONDS);
                glow = color((int) Math.round(22 * remaining), (int) Math.round(15 * remaining),
                        (int) Math.round(11 * remaining), (int) Math.round(5 * remaining));
            }
            if (!glow.equals(light.getColorLight())) {
                light.setColorLight(glow);
            }
        }
    }
}
