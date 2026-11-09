package steven.rangersnipers;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Shared reference is deliberate: all physical pellets belong to one paid shell. */
public record ScatterPellet(ShotgunLedger ledger, int index, double body, double head, double maxRange) implements Component<EntityStore> {
    @Override public ScatterPellet clone() { return this; }
}
