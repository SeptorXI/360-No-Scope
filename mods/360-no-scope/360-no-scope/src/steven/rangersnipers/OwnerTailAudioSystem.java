package steven.rangersnipers;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.EntityEventSystem;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.modules.projectile.component.ProjectileLaunchContext;
import com.hypixel.hytale.server.core.modules.projectile.event.ProjectileLaunchEvent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.bson.BsonDocument;
import org.joml.Vector3dc;

import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/** Sends the direct reports and a fixed-origin 3D return after one paid discharge. */
public final class OwnerTailAudioSystem extends EntityEventSystem<EntityStore, ProjectileLaunchEvent> {
    public record Profile(String primaryEventId, String abilityEventId,
                          String primaryLocalEventId, String primaryWorldEventId,
                          String abilityLocalEventId, String abilityWorldEventId,
                          String burstLocalEventId, String burstWorldEventId) {}

    private final Map<String, Profile> profiles;
    private final OwnerTailGate gate = new OwnerTailGate(error ->
        System.err.println("[360 No Scope] Shot audio route skipped: " + error));

    public OwnerTailAudioSystem(Map<String, Profile> profiles) {
        super(ProjectileLaunchEvent.class);
        this.profiles = Map.copyOf(profiles);
    }

    public Map<String, Profile> profiles() {
        return profiles;
    }

    public static OwnerTailAudioSystem fromResource(ClassLoader loader) {
        Map<String, Profile> profiles = new HashMap<>();
        try (var input = loader.getResourceAsStream("ranger-snipers-owner-tail-profiles.json")) {
            if (input == null) throw new IllegalStateException("Missing ranger-snipers-owner-tail-profiles.json");
            var document = BsonDocument.parse(new String(input.readAllBytes(), StandardCharsets.UTF_8));
            for (var value : document.getArray("Profiles")) {
                var row = value.asDocument();
                String marker = readId(row, "FlightMarker");
                boolean ability = row.containsKey("AbilityEventId");
                boolean burst = row.containsKey("BurstLocalEventId");
                if (row.containsKey("AbilityLocalEventId") != ability || row.containsKey("AbilityWorldEventId") != ability) {
                    throw new IllegalArgumentException("Incomplete ability audio binding for " + marker);
                }
                if (row.containsKey("BurstWorldEventId") != burst) {
                    throw new IllegalArgumentException("Incomplete burst audio binding for " + marker);
                }
                var profile = new Profile(readId(row, "PrimaryEventId"),
                    ability ? readId(row, "AbilityEventId") : null,
                    readId(row, "PrimaryLocalEventId"), readId(row, "PrimaryWorldEventId"),
                    ability ? readId(row, "AbilityLocalEventId") : null,
                    ability ? readId(row, "AbilityWorldEventId") : null,
                    burst ? readId(row, "BurstLocalEventId") : null,
                    burst ? readId(row, "BurstWorldEventId") : null);
                if (profiles.put(marker, profile) != null) throw new IllegalArgumentException("Duplicate audio flight marker");
            }
            if (profiles.size() != 59) throw new IllegalStateException("Expected 59 shot audio profiles");
        } catch (Throwable error) {
            profiles.clear();
            System.err.println("[360 No Scope] Shot audio profiles unavailable: " + error);
        }
        return new OwnerTailAudioSystem(profiles);
    }

    private static String readId(BsonDocument row, String key) {
        String id = row.getString(key).getValue();
        if (!id.matches("[A-Za-z0-9_]+")) throw new IllegalArgumentException("Invalid audio binding " + key);
        return id;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return TransformComponent.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> commands, ProjectileLaunchEvent event) {
        try {
            var type = event.getInteractionType();
            if (profiles.isEmpty() || !event.isLaunchedByWeapon()
                || (type != InteractionType.Primary && type != InteractionType.Ability1)) return;
            var owner = chunk.getReferenceTo(index);
            var projectile = event.getProjectileRef();
            // The launch context and scatter metadata are queued before this event.
            commands.run(actual -> dispatch(owner, projectile, type, actual));
        } catch (Throwable error) {
            gate.warn(error);
        }
    }

    private void dispatch(Ref<EntityStore> owner, Ref<EntityStore> projectile, InteractionType type,
                          Store<EntityStore> store) {
        try {
            if (owner == null || !owner.isValid() || projectile == null || !projectile.isValid()) return;
            var player = store.getComponent(owner, PlayerRef.getComponentType());
            var context = store.getComponent(projectile, ProjectileLaunchContext.getComponentType());
            if (context == null || !context.isLaunchedByWeapon() || context.getInteractionType() != type) return;
            var interactions = store.getComponent(projectile, Interactions.getComponentType());
            if (interactions == null) return;
            String marker = interactions.getInteractionId(InteractionType.ProjectileSpawn);
            if (marker == null) return;
            var profile = profiles.get(marker);
            if (profile == null) return;

            var pelletType = RangerSnipersPlugin.scatterComponentType();
            var pellet = pelletType == null ? null : store.getComponent(projectile, pelletType);
            int pelletIndex = pellet == null ? 0 : pellet.index();
            if (pelletIndex > 0) return;
            Object token = pellet == null ? projectile : pellet.ledger();
            gate.emitOnce(token, owner, pelletIndex, true,
                () -> playDischarge(player, owner, projectile, type, profile, store));
        } catch (Throwable error) {
            gate.warn(error);
        }
    }

    private void playDischarge(PlayerRef player, Ref<EntityStore> owner, Ref<EntityStore> projectile,
                               InteractionType type, Profile profile, Store<EntityStore> store) {
        boolean ability = type == InteractionType.Ability1;
        boolean burst = gate.continuesBurst(owner, !ability && profile.burstLocalEventId() != null);
        String localId = ability ? profile.abilityLocalEventId()
            : burst ? profile.burstLocalEventId() : profile.primaryLocalEventId();
        String worldId = ability ? profile.abilityWorldEventId()
            : burst ? profile.burstWorldEventId() : profile.primaryWorldEventId();
        String tailId = ability ? profile.abilityEventId() : profile.primaryEventId();

        // The dry shooter route works even if positional effects are unavailable.
        if (player != null) {
            safely(() -> {
                int local = soundIndex(localId);
                if (local > 0) SoundUtil.playSoundEvent2dToPlayer(player, local, SoundCategory.SFX);
            });
        }

        var flightType = RangerSnipersPlugin.flightComponentType();
        var flight = flightType == null ? null : store.getComponent(projectile, flightType);
        if (flight == null) return;
        var origin = flight.originCopy();
        if (!Double.isFinite(origin.x()) || !Double.isFinite(origin.y()) || !Double.isFinite(origin.z())) return;

        safely(() -> playNearby(soundIndex(worldId), owner, origin, store));
        // Preserve World reports for non-player shooters without adding an owner return.
        if (player == null) return;
        int tail = selectTail(tailId, origin, store);
        if (tail > 0) {
            // One shooter packet even if the current spatial index excludes the shooter.
            safely(() -> SoundUtil.playSoundEvent3dToPlayer(owner, tail, SoundCategory.SFX,
                origin.x(), origin.y(), origin.z(), 1, 1, store));
            safely(() -> playNearby(tail, owner, origin, store));
        }
    }

    private int selectTail(String eventId, Vector3dc origin, Store<EntityStore> store) {
        if (eventId == null) return 0;
        int covered = soundIndex(eventId);
        int open = soundIndex(eventId + "_Outdoor");
        if (open <= 0) return covered;
        try {
            var chunks = store.getExternalData().getWorld().getChunkStore();
            return ShotReturnEnvironment.openSky(chunks, origin) ? open : covered;
        } catch (RuntimeException failure) {
            gate.warn(failure);
            return covered;
        }
    }

    private static int soundIndex(String id) {
        if (id == null) return 0;
        var assets = SoundEvent.getAssetMap();
        int index = assets.getIndex(id);
        return index > 0 && assets.getAsset(index) != null ? index : 0;
    }

    private static void playNearby(int event, Ref<EntityStore> owner, Vector3dc origin, Store<EntityStore> store) {
        if (event > 0) SoundUtil.playSoundEvent3d(event, SoundCategory.SFX,
            origin.x(), origin.y(), origin.z(), 1, 1, listener -> !owner.equals(listener), store);
    }

    private void safely(Runnable play) {
        try {
            play.run();
        } catch (Throwable failure) {
            gate.warn(failure);
        }
    }
}
