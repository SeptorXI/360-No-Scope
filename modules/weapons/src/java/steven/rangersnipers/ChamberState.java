package steven.rangersnipers;

import com.hypixel.hytale.server.core.inventory.ItemStack;
import org.bson.*;
import java.util.UUID;

/** Persistent, per-ItemStack state. No player-global ammo resource. */
public final class ChamberState {
    public static final String KEY = "RS_Chamber";
    public record Profile(String weaponId, String ammoId, int capacity) {}
    public record State(String instanceId, int loaded, int revision) {}
    private ChamberState() {}

    public static State read(ItemStack stack, Profile profile) {
        if (stack == null || !stack.getItemId().equals(profile.weaponId()) || stack.getQuantity() != 1)
            throw new IllegalArgumentException("Wrong chamber receiver");
        BsonDocument metadata = stack.getMetadata();
        if (metadata == null || !metadata.containsKey(KEY)) return new State(null, 0, 0);
        BsonDocument own = metadata.getDocument(KEY);
        String id = own.getString("InstanceId").getValue();
        UUID.fromString(id);
        int loaded = own.getInt32("Loaded").getValue();
        int revision = own.getInt32("Revision").getValue();
        if (own.getInt32("Version").getValue() != 1 ||
            !own.getString("AmmoId").getValue().equals(profile.ammoId()) ||
            loaded < 0 || loaded > profile.capacity() || revision < 0)
            throw new IllegalArgumentException("Invalid chamber metadata");
        return new State(id, loaded, revision);
    }

    public static ItemStack initialize(ItemStack stack, Profile profile) {
        State old = read(stack, profile);
        return old.instanceId() != null ? stack : write(stack, profile,
                new State(UUID.randomUUID().toString(), 0, 0));
    }

    public static ItemStack withLoaded(ItemStack stack, Profile profile, int loaded) {
        State old = read(stack, profile);
        if (old.instanceId() == null || loaded < 0 || loaded > profile.capacity())
            throw new IllegalArgumentException("Invalid chamber transition");
        return write(stack, profile, new State(old.instanceId(), loaded, Math.addExact(old.revision(), 1)));
    }

    public static ItemStack consume(ItemStack stack, Profile profile, int cost) {
        State state = read(stack, profile);
        if (cost < 1 || state.loaded() < cost) throw new IllegalStateException("Reload required");
        return withLoaded(stack, profile, state.loaded() - cost);
    }

    private static ItemStack write(ItemStack stack, Profile profile, State state) {
        BsonDocument own = new BsonDocument("Version", new BsonInt32(1))
            .append("InstanceId", new BsonString(state.instanceId()))
            .append("AmmoId", new BsonString(profile.ammoId()))
            .append("Loaded", new BsonInt32(state.loaded()))
            .append("Revision", new BsonInt32(state.revision()));
        // Native method copies the complete existing metadata and all item fields.
        return stack.withMetadata(KEY, own);
    }
}
