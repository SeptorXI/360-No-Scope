package steven.rangersnipers;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.projectile.system.StandardPhysicsTickSystem;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Set;

/** Accumulates the server's simulated path segments after projectile physics. */
public final class FlightPathSystem extends EntityTickingSystem<EntityStore> {
    private final ComponentType<EntityStore, FlightState> flightType;
    public FlightPathSystem(ComponentType<EntityStore, FlightState> flightType) { this.flightType = flightType; }
    @Override public Query<EntityStore> getQuery() { return Query.and(flightType, TransformComponent.getComponentType()); }
    @Override public Set<Dependency<EntityStore>> getDependencies() {
        return Set.of(new SystemDependency<>(Order.AFTER, StandardPhysicsTickSystem.class));
    }
    @Override public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk,
                               Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        chunk.getComponent(index, flightType).recordStep(
            chunk.getComponent(index, TransformComponent.getComponentType()).getPosition());
    }
}
