package steven.riflesentry;

import com.hypixel.hytale.builtin.deployables.component.DeployableComponent;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.protocol.CombatTextUpdate;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.tracker.EntityTrackerSystems.EntityViewer;
import com.hypixel.hytale.server.core.modules.entityui.UIComponentList;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Sends normal floating combat text to the sentry owner for applied hits. */
final class SentryDamageNumbers extends DamageEventSystem {
    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return UIComponentList.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        var turret = RifleSentryPlugin.rifleSource(damage, store, buffer);
        if (turret == null) {
            return;
        }
        var deployable = buffer.getComponent(turret, DeployableComponent.getComponentType());
        var owner = deployable.getOwner();
        if (!RifleSentryPlugin.usable(owner, store)) {
            return;
        }
        var player = buffer.getComponent(owner, PlayerRef.getComponentType());
        var viewer = buffer.getComponent(owner, EntityViewer.getComponentType());
        var target = chunk.getReferenceTo(index);
        if (player == null || !player.isValid() || player.getReference() != owner
            || !player.getUuid().equals(deployable.getOwnerUUID())
            || viewer == null || !viewer.visible.contains(target)) {
            return;
        }
        var cause = DamageCause.getAssetMap().getAsset(damage.getDamageCauseIndex());
        var hitAngle = damage.getIfPresentMetaObject(Damage.HIT_ANGLE);
        viewer.queueUpdate(target, new CombatTextUpdate(hitAngle == null ? 0f : hitAngle,
            Integer.toString((int) Math.floor(damage.getAmount())),
            cause == null ? null : cause.resolveDamageTextColor()));
    }
}
