package steven.oblivionst;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Transient six-second combat state; deliberately not serialized to player saves. */
public final class VenomState implements Component<EntityStore> {
    public final VenomLedger<Ref<EntityStore>> ledger;
    public VenomState(){ledger=new VenomLedger<>();}
    private VenomState(VenomLedger<Ref<EntityStore>> ledger){this.ledger=ledger;}
    @Override public VenomState clone(){return new VenomState(ledger.copy());}
}
