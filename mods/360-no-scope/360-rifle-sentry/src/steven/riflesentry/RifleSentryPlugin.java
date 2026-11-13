package steven.riflesentry;

import com.airijko.endlessleveling.EndlessLeveling;
import com.airijko.endlessleveling.systems.MobDamageFloorSystem;
import com.hypixel.hytale.builtin.deployables.component.DeployableComponent;
import com.hypixel.hytale.builtin.deployables.config.DeployableConfig;
import com.hypixel.hytale.builtin.deployables.config.DeployableTurretConfig;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.dependency.SystemGroupDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;

public final class RifleSentryPlugin extends JavaPlugin {
    private static final String SENTRY_ID = "mmo_sentry_turret";
    private static final String RIFLE_MODEL = "AS_Rifle_Sentry";
    private static final String WEAPON_CATEGORY = "crossbow";

    public RifleSentryPlugin(JavaPluginInit init) {
        super(init);
    }

    @Override
    protected void setup() {
        getCodecRegistry(DeployableConfig.CODEC).register("RifleSentryHostileTurret", SentryTargeting.class, SentryTargeting.CODEC);
        getEntityStoreRegistry().registerSystem(new ScaleOwnerDamage());
        getEntityStoreRegistry().registerSystem(new SentryTargeting.DamageGuard());
        getEntityStoreRegistry().registerSystem(new PreserveFractionalDamage());
        getEntityStoreRegistry().registerSystem(new SentryDamageNumbers());
        getEntityStoreRegistry().registerSystem(new SentryThirdHit());
        getEntityStoreRegistry().registerSystem(new SentryTargeting.OwnerHitMark());
        getEntityStoreRegistry().registerSystem(new SentryTargeting.LevelFloorSpawn());
        getEntityStoreRegistry().registerSystem(new SentryMuzzleFlash());
    }

    static Ref<EntityStore> rifleSource(Damage damage, Store<EntityStore> store,
                                       CommandBuffer<EntityStore> buffer) {
        if (damage.isCancelled() || !positiveFinite(damage.getAmount())
            || !(damage.getSource() instanceof Damage.EntitySource source)
            || source.getClass() != Damage.EntitySource.class
            || damage.getDamageCauseIndex() != DamageCause.getAssetMap().getIndex("Physical")) {
            return null;
        }
        Ref<EntityStore> ref = source.getRef();
        if (!usable(ref, store)) {
            return null;
        }
        DeployableComponent deployable = buffer.getComponent(ref, DeployableComponent.getComponentType());
        return isRifleSentry(deployable) ? ref : null;
    }

    static boolean isRifleSentry(DeployableComponent deployable) {
        return deployable != null && deployable.getConfig() instanceof DeployableTurretConfig config
            && SENTRY_ID.equals(config.getId()) && config.getModel() != null
            && RIFLE_MODEL.equals(config.getModel().getModelAssetId());
    }

    static boolean usable(Ref<EntityStore> ref, Store<EntityStore> store) {
        return ref != null && ref.getStore() == store && ref.isValid();
    }

    private static boolean positiveFinite(float amount) {
        return amount > 0 && Float.isFinite(amount);
    }

    public static final class ScaleOwnerDamage extends DamageEventSystem {
        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public SystemGroup<EntityStore> getGroup() {
            return DamageModule.get().getGatherDamageGroup();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, Damage damage) {
            Ref<EntityStore> turret = rifleSource(damage, store, buffer);
            if (turret == null) {
                return;
            }
            DeployableComponent deployable = buffer.getComponent(turret, DeployableComponent.getComponentType());
            Ref<EntityStore> owner = deployable.getOwner();
            if (!usable(owner, store)) {
                return;
            }
            PlayerRef player = buffer.getComponent(owner, PlayerRef.getComponentType());
            var ownerId = deployable.getOwnerUUID();
            if (player == null || !player.isValid() || player.getReference() != owner
                || ownerId == null || !ownerId.equals(player.getUuid())) {
                return;
            }
            EndlessLeveling leveling = EndlessLeveling.getInstance();
            if (leveling == null || leveling.getPlayerDataManager() == null || leveling.getClassManager() == null
                || leveling.getSkillManager() == null) {
                return;
            }
            var data = leveling.getPlayerDataManager().get(ownerId);
            if (data == null) {
                return;
            }

            double classMultiplier = leveling.getClassManager().getWeaponDamageMultiplier(data, WEAPON_CATEGORY);
            if (!Double.isFinite(classMultiplier) || classMultiplier < 0) {
                return;
            }
            var skills = leveling.getSkillManager();
            double flatStrength = skills.getFlatStrengthBonus(data);
            if (!Double.isFinite(flatStrength)) {
                return;
            }
            double baseDamage = Math.max(0d, damage.getAmount() + flatStrength * 0.5);
            float classDamage = (float) (baseDamage * classMultiplier);
            if (!Float.isFinite(classDamage)) {
                return;
            }
            float strengthDamage = skills.applyStrengthModifier(classDamage, data);
            if (!Float.isFinite(strengthDamage) || strengthDamage < 0) {
                return;
            }
            float scaled = skills.applyCriticalHit(data, strengthDamage).damage;
            if (Float.isFinite(scaled) && scaled >= 0) {
                damage.setAmount(scaled);
            }
        }
    }

    public static final class PreserveFractionalDamage extends DamageEventSystem {
        // Native Ref keys use identity equality. Neither weak map's values retain its keys.
        private final Map<Ref<EntityStore>, Map<Ref<EntityStore>, Double>> remainders = new WeakHashMap<>();

        @Override
        public Query<EntityStore> getQuery() {
            return Query.any();
        }

        @Override
        public Set<Dependency<EntityStore>> getDependencies() {
            // Endless Leveling processes player defense and its newcomer damage cap outside the native filter group.
            return Set.of(new SystemGroupDependency<>(Order.AFTER, DamageModule.get().getFilterDamageGroup()),
                          new SystemDependency<>(Order.AFTER, MobDamageFloorSystem.class),
                          new SystemDependency<>(Order.BEFORE, DamageSystems.ApplyDamage.class));
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, Damage damage) {
            Ref<EntityStore> turret = rifleSource(damage, store, buffer);
            if (turret == null) {
                return;
            }
            Ref<EntityStore> target = chunk.getReferenceTo(index);
            synchronized (remainders) {
                // ApplyDamage rounds each event. Spend only whole HP and keep the filtered remainder.
                Map<Ref<EntityStore>, Double> hits = remainders.computeIfAbsent(turret, ignored -> new WeakHashMap<>());
                double total = damage.getAmount() + hits.getOrDefault(target, 0d);
                double whole = Math.floor(total);
                hits.put(target, total - whole);
                damage.setAmount((float) whole);
            }
        }
    }
}
