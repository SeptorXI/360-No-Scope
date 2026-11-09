package steven.rangersnipers;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.Interactions;
import com.hypixel.hytale.server.core.modules.projectile.component.Projectile;
import com.hypixel.hytale.server.core.modules.projectile.component.PredictedProjectile;
import com.hypixel.hytale.server.core.modules.projectile.config.StandardPhysicsProvider;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Runs inside native entity addition, before any projectile physics tick. */
public final class FlightOriginSystem extends HolderSystem<EntityStore> {
    private final ComponentType<EntityStore, FlightState> flightType;
    public FlightOriginSystem(ComponentType<EntityStore, FlightState> flightType) { this.flightType = flightType; }
    @Override public Query<EntityStore> getQuery() {
        return Query.and(Projectile.getComponentType(), Interactions.getComponentType(),
            TransformComponent.getComponentType(), StandardPhysicsProvider.getComponentType());
    }
    @Override public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
        if (holder.getComponent(flightType) != null) return;
        var interactions = holder.getComponent(Interactions.getComponentType());
        var profile = RangerSnipersPlugin.FLIGHT_PROFILES.get(interactions.getInteractionId(InteractionType.ProjectileSpawn));
        if (profile == null) return;
        var transform = holder.getComponent(TransformComponent.getComponentType());
        var physics = holder.getComponent(StandardPhysicsProvider.getComponentType());
        var originalImpact = physics.getImpactConsumer();
        boolean predicted=holder.getComponent(PredictedProjectile.getComponentType())!=null;
        // Native predicted projectiles deliberately have no server callback:
        // their validated client ProjectileHit chain supplies final contact.
        // Missing callbacks must never abort Store.addEntity/world ticking.
        FlightState flight = new FlightState(profile, transform.getPosition(), originalImpact==null, predicted);
        holder.addComponent(flightType, flight);
        attachImpactHook(physics,flight);
    }
    static boolean attachImpactHook(StandardPhysicsProvider physics,FlightState flight) {
        if(flight.hasImpactHook())return true;
        var originalImpact=physics.getImpactConsumer();
        if(originalImpact==null)return false;
        // Freeze only the final partial segment, before the native callback
        // schedules an impact interaction or physics writes another endpoint.
        physics.setImpactConsumer((ref, contact, block, target, detail, buffer) -> {
            flight.finishImpact(contact);
            originalImpact.onImpact(ref, contact, block, target, detail, buffer);
        });
        flight.markImpactHookInstalled();
        return true;
    }
    @Override public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {}
}
