package steven.oblivionst;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.*;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Provenance is captured before filters; rejected events never gain a stack. */
public final class VenomCaptureSystem extends DamageEventSystem {
    @Override public Query<EntityStore> getQuery(){return Query.any();}
    @Override public SystemGroup<EntityStore> getGroup(){return DamageModule.get().getGatherDamageGroup();}
    @Override public void handle(int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer,Damage damage){
        DaggerDamageInteraction.capture(damage,chunk.getReferenceTo(index));
    }
}
