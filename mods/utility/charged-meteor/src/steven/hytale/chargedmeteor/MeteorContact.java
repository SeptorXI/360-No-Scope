package steven.hytale.chargedmeteor;

import com.hypixel.hytale.builtin.abilities.entity.AbilityEntityRepeat;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.interaction.InteractionModule;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.RootInteraction;
import com.hypixel.hytale.server.core.modules.time.TimeResource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.time.Instant;
import org.joml.Vector4d;

record MeteorContact(Instant landsAt) implements Component<EntityStore> {
    static final long FALL_MILLISECONDS = 3280;

    @Override
    public MeteorContact clone() {
        return this;
    }

    static final class ContactSystem extends EntityTickingSystem<EntityStore> {
        private final ComponentType<EntityStore, MeteorContact> contactType;

        ContactSystem(ComponentType<EntityStore, MeteorContact> contactType) {
            this.contactType = contactType;
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.and(contactType, AbilityEntityRepeat.getComponentType(),
                    TransformComponent.getComponentType(), InteractionModule.get().getInteractionManagerComponent());
        }

        @Override
        public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk,
                         Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
            var contact = chunk.getComponent(index, contactType);
            if (buffer.getResource(TimeResource.getResourceType()).getNow().isBefore(contact.landsAt())) {
                return;
            }

            var proxy = chunk.getReferenceTo(index);
            buffer.removeComponent(proxy, contactType);
            var caster = chunk.getComponent(index, AbilityEntityRepeat.getComponentType()).getCasterRef();
            if (!caster.isValid()) {
                return;
            }
            var manager = chunk.getComponent(index, InteractionModule.get().getInteractionManagerComponent());
            var root = RootInteraction.getAssetMap().getAsset("ChargedMeteor_ImpactRoot");
            if (root == null) {
                return;
            }
            var context = InteractionContext.forProxyEntity(manager, caster, proxy, buffer);
            var position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
            context.getMetaStore().putMetaObject(Interaction.HIT_LOCATION,
                    new Vector4d(position.x, position.y, position.z, 1));
            manager.queueExecuteChain(manager.initChain(InteractionType.ProjectileMiss, context, root, true));
        }
    }
}
