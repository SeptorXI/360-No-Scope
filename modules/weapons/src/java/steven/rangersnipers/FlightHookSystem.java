package steven.rangersnipers;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.projectile.config.StandardPhysicsProvider;
import com.hypixel.hytale.server.core.modules.projectile.system.StandardPhysicsTickSystem;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Set;

/** Retry genuinely deferred server callbacks before physics, never fabricate one. */
public final class FlightHookSystem extends EntityTickingSystem<EntityStore> {
    private final ComponentType<EntityStore,FlightState> flightType;
    public FlightHookSystem(ComponentType<EntityStore,FlightState> flightType){this.flightType=flightType;}
    @Override public Query<EntityStore> getQuery(){return Query.and(flightType,StandardPhysicsProvider.getComponentType());}
    @Override public Set<Dependency<EntityStore>> getDependencies(){return Set.of(new SystemDependency<>(Order.BEFORE,StandardPhysicsTickSystem.class));}
    @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> commands){
        var flight=chunk.getComponent(index,flightType);
        if(flight.isPredicted()||flight.hasImpactHook())return;
        if(!FlightOriginSystem.attachImpactHook(chunk.getComponent(index,StandardPhysicsProvider.getComponentType()),flight))
            RangerSnipersPlugin.reportFailure(flight.profile().weaponId(),new IllegalStateException("Native callback not yet available; preserving flight until validated native hit metadata"));
    }
}
