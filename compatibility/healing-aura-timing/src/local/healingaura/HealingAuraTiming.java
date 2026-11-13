package local.healingaura;

import com.airijko.endlessleveling.EndlessLeveling;
import com.airijko.endlessleveling.api.AbilityBridge;
import com.airijko.endlessleveling.passives.PassiveManager.PassiveRuntimeState;
import com.airijko.endlessleveling.passives.type.HealingAuraPassive;
import com.airijko.endlessleveling.systems.PassiveRegenSystem;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

public final class HealingAuraTiming extends JavaPlugin {
    private static final String SUPPORTED_VERSION = "14.5.6";

    public HealingAuraTiming(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        var core = EndlessLeveling.getInstance();
        if (core == null || !SUPPORTED_VERSION.equals(core.getManifest().getVersion().toString())) {
            getLogger().atWarning().log("Healing Aura timer repair requires Endless Leveling %s. Skipping registration.",
                SUPPORTED_VERSION);
            return;
        }
        getEntityStoreRegistry().registerSystem(new AuraTimerRepair(core));
        getLogger().atInfo().log("Registered Healing Aura timer repair after Endless Leveling's passive tick.");
    }

    static long reconcile(long lastPulse, long observed, boolean damagePaused) {
        if (observed == 0L || observed < lastPulse) {
            return 0L;
        }
        if (damagePaused || (lastPulse != 0L && observed - lastPulse < HealingAuraPassive.pulseIntervalMillis())) {
            return lastPulse;
        }
        return observed;
    }

    private static final class AuraTimerRepair extends EntityTickingSystem<EntityStore> {
        private final EndlessLeveling core;
        private final Map<PassiveRuntimeState, Long> lastPulses =
            Collections.synchronizedMap(new WeakHashMap<>());

        private AuraTimerRepair(EndlessLeveling core) {
            this.core = core;
        }

        @Override
        public Set<Dependency<EntityStore>> getDependencies() {
            return Set.of(new SystemDependency<>(Order.AFTER, PassiveRegenSystem.class));
        }

        @Override
        public Query<EntityStore> getQuery() {
            return PlayerRef.getComponentType();
        }

        @Override
        public void tick(float timeStep, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                         CommandBuffer<EntityStore> buffer) {
            if (AbilityBridge.isRegistered()) {
                return;
            }
            var player = chunk.getComponent(index, PlayerRef.getComponentType());
            if (player == null || !player.isValid()) {
                return;
            }
            var runtime = core.getPassiveManager().getRuntimeStateIfPresent(player.getUuid());
            if (runtime == null) {
                return;
            }
            long lastPulse = lastPulses.getOrDefault(runtime, 0L);
            long observed = runtime.getPartyMendingLastPulseMillis();
            if (observed == lastPulse) {
                return;
            }

            boolean damagePaused = false;
            if (observed > lastPulse && (lastPulse == 0L ||
                    observed - lastPulse >= HealingAuraPassive.pulseIntervalMillis())) {
                var playerData = core.getPlayerDataManager().get(player.getUuid());
                if (playerData != null) {
                    var snapshot = core.getArchetypePassiveManager().getSnapshot(playerData);
                    damagePaused = HealingAuraPassive.isDamagePaused(snapshot, runtime, observed);
                }
            }
            long repaired = reconcile(lastPulse, observed, damagePaused);
            if (repaired != observed) {
                runtime.setPartyMendingLastPulseMillis(repaired);
            }
            if (repaired == 0L) {
                lastPulses.remove(runtime);
            } else if (repaired != lastPulse) {
                lastPulses.put(runtime, repaired);
            }
        }
    }
}
