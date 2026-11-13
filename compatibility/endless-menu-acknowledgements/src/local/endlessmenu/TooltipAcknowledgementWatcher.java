package local.endlessmenu;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.Packet;
import com.hypixel.hytale.protocol.packets.interface_.Page;
import com.hypixel.hytale.protocol.packets.interface_.SetPage;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.entity.entities.player.pages.PageManager;
import com.hypixel.hytale.server.core.io.adapter.PlayerPacketWatcher;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.lang.reflect.Field;
import java.util.Iterator;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;

/** Accounts for one raw close sent by the reviewed Endless Leveling tooltip flush. */
public final class TooltipAcknowledgementWatcher implements PlayerPacketWatcher {
    private static final String INVENTORY = "com.airijko.endlessleveling.ui.InventoryUIPage";
    private static final String PAGE_MANAGER = PageManager.class.getName();
    private final Field acknowledgementField;
    private final Consumer<String> warning;
    private final AtomicBoolean warned = new AtomicBoolean();
    private final StackWalker stackWalker = StackWalker.getInstance();

    public TooltipAcknowledgementWatcher(Consumer<String> warning) throws ReflectiveOperationException {
        this.warning = java.util.Objects.requireNonNull(warning);
        acknowledgementField = PageManager.class.getDeclaredField("customPageRequiredAcknowledgments");
        if (acknowledgementField.getType() != AtomicInteger.class)
            throw new NoSuchFieldException("Unexpected custom page acknowledgement field type");
        if (!acknowledgementField.trySetAccessible())
            throw new IllegalAccessException("Custom page acknowledgement field is inaccessible");
    }

    @Override
    public void accept(PlayerRef playerRef, Packet packet) {
        if (!(packet instanceof SetPage close) || close.page != Page.None || playerRef == null)
            return;
        try {
            if (!isReviewedRawClose()) return;
            Ref<EntityStore> ref = playerRef.getReference();
            if (ref == null || !ref.isValid()) return;
            Store<EntityStore> store = ref.getStore();
            if (store == null || store.getExternalData() == null) return;
            var world = store.getExternalData().getWorld();
            if (world == null || !world.isInThread()) return;
            if (playerRef.getReference() != ref || !ref.isValid() || ref.getStore() != store) return;
            Player player = store.getComponent(ref, Player.getComponentType());
            if (player == null || player.getPlayerRef() != playerRef) return;
            PageManager manager = player.getPageManager();
            // The affected vendor path has already called resetPages. Never touch a live page.
            if (manager == null || manager.getCustomPage() != null) return;
            AtomicInteger acknowledgements = (AtomicInteger) acknowledgementField.get(manager);
            if (acknowledgements == null) return;
            acknowledgements.incrementAndGet();
        } catch (ReflectiveOperationException | RuntimeException failure) {
            // An observation failure must never prevent delivery of the original packet.
            if (warned.compareAndSet(false, true)) {
                try { warning.accept("Endless menu acknowledgement helper could not account for a tooltip close; original packet delivery continues."); }
                catch (RuntimeException ignored) { }
            }
        }
    }

    private boolean isReviewedRawClose() {
        return stackWalker.walk(frames -> {
            boolean tooltipFlush = false;
            Iterator<StackWalker.StackFrame> iterator = frames.iterator();
            while (iterator.hasNext()) {
                StackWalker.StackFrame frame = iterator.next();
                if (PAGE_MANAGER.equals(frame.getClassName())
                        && ("setPage".equals(frame.getMethodName()) || "closePage".equals(frame.getMethodName())))
                    return false;
                if (INVENTORY.equals(frame.getClassName()) && "lambda$flushTooltip$0".equals(frame.getMethodName()))
                    tooltipFlush = true;
            }
            return tooltipFlush;
        });
    }
}
