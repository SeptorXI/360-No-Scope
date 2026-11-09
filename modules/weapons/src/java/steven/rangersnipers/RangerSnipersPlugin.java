package steven.rangersnipers;

import com.hypixel.hytale.server.core.plugin.*;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.bson.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.logging.Level;

public final class RangerSnipersPlugin extends JavaPlugin {
    static final Map<String, ChamberState.Profile> PROFILES = new HashMap<>();
    static final Map<String, FlightState.Profile> FLIGHT_PROFILES = new HashMap<>();
    static ComponentType<EntityStore, FlightState> flightType;
    static ComponentType<EntityStore, ScatterPellet> scatterType;
    static EternalShotBridge eternalShot;
    static String bridgeFailure;
    static RangerSnipersPlugin instance;
    private static final Set<String> REPORTED = java.util.concurrent.ConcurrentHashMap.newKeySet();
    public RangerSnipersPlugin(JavaPluginInit init) { super(init); }
    @Override protected void setup() {
        instance = this;
        try (InputStream input = getClass().getClassLoader().getResourceAsStream("ranger-snipers-reload-profiles.json")) {
            if (input == null) throw new IllegalStateException("Missing canonical reload profiles");
            BsonDocument document = BsonDocument.parse(new String(input.readAllBytes(), StandardCharsets.UTF_8));
            for (BsonValue value : document.getArray("Profiles")) {
                BsonDocument row = value.asDocument();
                ChamberState.Profile profile = new ChamberState.Profile(row.getString("WeaponId").getValue(),
                    row.getString("AmmoId").getValue(), row.getInt32("Capacity").getValue());
                if (profile.capacity() < 1 || profile.capacity() > 40 || PROFILES.put(profile.weaponId(), profile) != null)
                    throw new IllegalStateException("Invalid reload profile");
                if (!"traveledPath".equals(row.getString("FalloffMetric").getValue()))
                    throw new IllegalStateException("Unsupported sniper falloff metric");
                List<FlightState.Point> points = new ArrayList<>();
                for (BsonValue pointValue : row.getArray("FalloffPoints")) {
                    BsonDocument point = pointValue.asDocument();
                    points.add(new FlightState.Point(point.getNumber("Distance").doubleValue(),
                        point.getNumber("Multiplier").doubleValue()));
                }
                FlightState.Profile flight = new FlightState.Profile(profile.weaponId(),
                    row.getString("FlightMarker").getValue(), points);
                if (FLIGHT_PROFILES.put(flight.markerId(), flight) != null)
                    throw new IllegalStateException("Duplicate flight marker");
            }
            if (PROFILES.size() != 54) throw new IllegalStateException("Expected 54 reload profiles");
            if (FLIGHT_PROFILES.size() != 54) throw new IllegalStateException("Expected 54 flight profiles");
        } catch (Exception failure) { throw new IllegalStateException("Cannot load Ranger sniper chamber profiles", failure); }
        try { eternalShot = new EternalShotBridge(); }
        catch (Exception failure) {
            bridgeFailure = "Ranger sniper firing disabled: SimpleEnchantments 1.2.1 Eternal Shot bridge could not initialize: " + failure;
            getLogger().at(Level.SEVERE).log(bridgeFailure);
        }
        getCodecRegistry(Interaction.CODEC).register("RSChamber", ChamberInteraction.class, ChamberInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register("RSAim", AimInteraction.class, AimInteraction.CODEC);
        scatterType = getEntityStoreRegistry().registerComponent(ScatterPellet.class, () -> {
            throw new IllegalStateException("ScatterPellet requires its shell ledger");
        });
        getCodecRegistry(Interaction.CODEC).register("ASScatter", ScatterInteraction.class, ScatterInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register("ASScatterHit", ScatterHitInteraction.class, ScatterHitInteraction.CODEC);
        flightType = getEntityStoreRegistry().registerComponent(FlightState.class, () -> {
            throw new IllegalStateException("FlightState requires a captured projectile origin");
        });
        getEntityStoreRegistry().registerSystem(new FlightOriginSystem(flightType));
        getEntityStoreRegistry().registerSystem(new FlightHookSystem(flightType));
        getEntityStoreRegistry().registerSystem(new FlightPathSystem(flightType));
        getEntityStoreRegistry().registerSystem(OwnerTailAudioSystem.fromResource(getClass().getClassLoader()));
        getCodecRegistry(Interaction.CODEC).register("RSFalloff", FalloffInteraction.class, FalloffInteraction.CODEC);
        getLogger().at(Level.INFO).log("Ranger sniper chamber codec registered; per-item profiles=%d, EternalShot bridge=%s", PROFILES.size(), eternalShot != null);
    }
    static void reportFailure(String weaponId, RuntimeException failure) {
        String message = "Ranger sniper chamber action rejected for " + weaponId + ": " + failure;
        if (instance != null && REPORTED.add(message)) instance.getLogger().at(Level.WARNING).log(message);
    }
    public static boolean bridgeReady() { return eternalShot != null; }
    public static ComponentType<EntityStore, FlightState> flightComponentType() { return flightType; }
    public static ComponentType<EntityStore, ScatterPellet> scatterComponentType() { return scatterType; }
    public static Collection<FlightState.Profile> flightProfiles() { return List.copyOf(FLIGHT_PROFILES.values()); }
}
