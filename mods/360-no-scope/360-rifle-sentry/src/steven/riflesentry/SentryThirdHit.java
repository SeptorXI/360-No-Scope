package steven.riflesentry;

import com.airijko.endlessleveling.bossframework.BossBarRegistry;
import com.airijko.endlessleveling.ecs.components.CcDiminishingComponent;
import com.airijko.endlessleveling.ecs.components.DungeonBossComponent;
import com.hypixel.hytale.assetstore.AssetRegistry;
import com.hypixel.hytale.builtin.encountermanager.EncounterBossBarState;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.entity.component.BoundingBox;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.InteractionModule;
import com.hypixel.hytale.server.core.universe.world.ParticleUtil;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import java.util.Map;
import java.util.WeakHashMap;
import org.joml.Vector3d;
import org.joml.Vector3dc;

/** Every third applied round on a target releases a charged impact. */
final class SentryThirdHit extends DamageEventSystem {
    private static final MetaKey<Vector3d> PROJECTILE_CONTACT = Damage.META_REGISTRY.registerMetaObject();
    private static final String IMPACT = "AS_Rifle_Sentry_ChargedImpact";
    private static final String ELIGIBLE = "Hit_Interrupt_Eligible";
    private static final String FLINCH = "Hit_Interrupt_Flinch";
    private static final String STUNNED = "Hit_Interrupt_Stunned";
    private static final String REACTION_A = "Hit_Interrupt_Recent_Reaction_A";
    private static final String REACTION_B = "Hit_Interrupt_Recent_Reaction_B";
    private static final String RECOVERY = "Hit_Interrupt_Recovery_Pending";
    private static final String ENRAGED = "Hit_Interrupt_Enraged";
    private static final String PROTECTED = "Hit_Interrupt_Protected_Attack";
    private final Map<Ref<EntityStore>, Map<Ref<EntityStore>, Integer>> landed = new WeakHashMap<>();

    static void markProjectile(Damage damage, Vector3dc position) {
        damage.putMetaObject(PROJECTILE_CONTACT,
            position != null && position.isFinite() ? new Vector3d(position) : new Vector3d(Double.NaN));
    }

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return Query.and(NPCEntity.getComponentType(), TransformComponent.getComponentType(),
            EntityStatMap.getComponentType());
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        var contact = damage.getIfPresentMetaObject(PROJECTILE_CONTACT);
        if (contact == null || Boolean.TRUE.equals(damage.getIfPresentMetaObject(Damage.BLOCKED))) {
            return;
        }
        var turret = RifleSentryPlugin.rifleSource(damage, store, buffer);
        if (turret == null) {
            return;
        }
        var target = chunk.getReferenceTo(index);
        synchronized (landed) {
            var hits = landed.computeIfAbsent(turret, ignored -> new WeakHashMap<>());
            int count = hits.getOrDefault(target, 0) + 1;
            if (count < 3) {
                hits.put(target, count);
                return;
            }
            hits.remove(target);
        }

        if (!contact.isFinite()) {
            contact = new Vector3d(chunk.getComponent(index, TransformComponent.getComponentType()).getPosition());
            var bounds = chunk.getComponent(index, BoundingBox.getComponentType());
            if (bounds != null) {
                contact.add(bounds.getBoundingBox().middleX(), bounds.getBoundingBox().middleY(),
                    bounds.getBoundingBox().middleZ());
            }
        }
        ParticleUtil.spawnParticleEffect(IMPACT, contact, buffer);
        var health = chunk.getComponent(index, EntityStatMap.getComponentType()).get(DefaultEntityStatTypes.getHealth());
        if (health != null && health.get() > health.getMin()
            && !hasComponent(target, DeathComponent.getComponentType(), buffer)) {
            stagger(target, buffer);
        }
    }

    private static void stagger(Ref<EntityStore> target, CommandBuffer<EntityStore> buffer) {
        var effects = buffer.getComponent(target, EffectControllerComponent.getComponentType());
        if (effects == null || !has(effects, ELIGIBLE) || has(effects, FLINCH) || has(effects, STUNNED)
            || has(effects, RECOVERY) || has(effects, ENRAGED) || has(effects, PROTECTED)
            || hasComponent(target, DungeonBossComponent.getComponentType(), buffer)
            || hasComponent(target, CcDiminishingComponent.getComponentType(), buffer)
            || hasComponent(target, EncounterBossBarState.getComponentType(), buffer)
            || BossBarRegistry.get().get(target) != null
            || !apply(effects, target, FLINCH, buffer)) {
            return;
        }
        apply(effects, target, STUNNED, buffer);
        interruptAttack(target, buffer);
        if (!has(effects, REACTION_A)) {
            apply(effects, target, REACTION_A, buffer);
        } else if (!has(effects, REACTION_B)) {
            apply(effects, target, REACTION_B, buffer);
        } else {
            effects.removeEffect(target, effectIndex(REACTION_A), buffer);
            effects.removeEffect(target, effectIndex(REACTION_B), buffer);
            apply(effects, target, RECOVERY, buffer);
        }
    }

    private static void interruptAttack(Ref<EntityStore> target, CommandBuffer<EntityStore> buffer) {
        var interactions = buffer.getComponent(target, InteractionModule.get().getInteractionManagerComponent());
        if (interactions == null) {
            return;
        }
        int attack = AssetRegistry.getOrCreateTagIndex("Attack");
        for (var chain : interactions.getChains().values()) {
            var root = chain.getInitialRootInteraction();
            if (root != null && root.getData() != null && root.getData().getExpandedTagIndexes().contains(attack)) {
                interactions.cancelChains(chain);
            }
        }
    }

    private static int effectIndex(String id) {
        return EntityEffect.getAssetMap().getIndex(id);
    }

    private static boolean has(EffectControllerComponent effects, String id) {
        int index = effectIndex(id);
        return index >= 0 && effects.hasEffect(index);
    }

    private static boolean apply(EffectControllerComponent effects, Ref<EntityStore> target, String id,
                                 CommandBuffer<EntityStore> buffer) {
        var effect = EntityEffect.getAssetMap().getAsset(id);
        return effect != null && effects.addEffect(target, effect, buffer);
    }

    private static <T extends Component<EntityStore>> boolean hasComponent(Ref<EntityStore> target,
        ComponentType<EntityStore, T> type, CommandBuffer<EntityStore> buffer) {
        return type != null && buffer.getComponent(target, type) != null;
    }
}
