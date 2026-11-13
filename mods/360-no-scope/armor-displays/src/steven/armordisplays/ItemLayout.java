package steven.armordisplays;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hypixel.hytale.math.shape.Box;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.asset.common.CommonAsset;
import com.hypixel.hytale.server.core.asset.common.CommonAssetRegistry;
import com.hypixel.hytale.server.core.asset.type.item.config.Item;
import com.hypixel.hytale.server.core.asset.type.model.config.Model;
import com.hypixel.hytale.server.core.asset.type.model.config.ModelAttachment;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import org.joml.Matrix4d;
import org.joml.Quaterniond;
import org.joml.Vector3d;

/** Read-only model measurements normalize arbitrary mod weapon attachment roots. */
public final class ItemLayout {
    public record Placement(Model model, Rotation3f rotation, Vector3d center, double halfDepth) {}
    private record Geometry(Box bounds, List<Matrix4d> shapes, Vector3d grip) {}
    private record CachedGeometry(CommonAsset asset, CompletableFuture<Geometry> future) {}
    private record GripSection(double minX, double maxX) {
        GripSection merge(GripSection other) {
            return new GripSection(minX, Math.max(maxX, other.maxX));
        }
        double distanceTo(double x) {
            return Math.max(0, Math.max(minX - x, x - maxX));
        }
    }
    private static final Map<String, CachedGeometry> CACHE = new ConcurrentHashMap<>();
    // Both rack models put their grips at y=35 and their weapon midpoints at y=30.
    private static final double RACK_GRIP_OFFSET = 5.0 / 32;
    private ItemLayout() {}
    public static CompletableFuture<Box> bounds(String path) {
        return geometry(path).thenApply(Geometry::bounds);
    }
    private static CompletableFuture<Geometry> geometry(String path) {
        CommonAsset asset = CommonAssetRegistry.getByName(path);
        if (asset == null) {
            CACHE.remove(path);
            return CompletableFuture.failedFuture(new IllegalArgumentException("Missing model: " + path));
        }
        CachedGeometry cached = CACHE.compute(path, (key, previous) -> {
            if (previous != null && previous.asset() == asset
                && !previous.future().isCompletedExceptionally() && !previous.future().isCancelled())
                return previous;
            return new CachedGeometry(asset, asset.getBlob().thenApply(ItemLayout::measureGeometry));
        });
        cached.future().whenComplete((geometry, failure) -> {
            if (failure != null) CACHE.remove(path, cached);
        });
        return cached.future();
    }
    public static Placement placement(Item item, String kind) {
        if (item.getModel() == null || item.getTexture() == null)
            throw new IllegalArgumentException("Weapon has no display model/texture: " + item.getId());
        CompletableFuture<Geometry> pending = geometry(item.getModel());
        if (!pending.isDone()) return null;
        Geometry geometry = pending.join();
        Box raw = geometry.bounds();
        boolean rack = "Rack".equals(kind);
        Rotation3f rotation = new Rotation3f();
        double width = raw.width(), height = raw.height(), depth = raw.depth();
        float quarterTurn = (float) (Math.PI / 2);
        if (rack) {
            if (width > height && width >= depth) rotation.setRoll(-quarterTurn);
            else if (depth > height) rotation.setPitch(-quarterTurn);
        } else {
            if (height >= width && height >= depth) rotation.setRoll(-quarterTurn);
            else if (depth >= width && depth >= height) rotation.setYaw(quarterTurn);
        }
        Box aligned = raw.enclosingRotatedAABB(rotation.pitch(),rotation.yaw(),rotation.roll());
        if (rack && aligned.depth() > aligned.width()) {
            // Present the broad side of the upright weapon to the front of the rack.
            rotation.setYaw(quarterTurn);
            // The displayed pose applies this yaw after the initial quarter-turn.
            aligned = aligned.enclosingRotatedAABB(0, quarterTurn, 0);
        }
        double maxDimension = Math.max(aligned.width(), Math.max(aligned.height(), aligned.depth()));
        if (!Double.isFinite(maxDimension) || maxDimension <= 0) throw new IllegalArgumentException("Empty weapon model");
        double sourceScale = item.getScale() > 0 && Float.isFinite(item.getScale()) ? item.getScale() : 1;
        double fit = rack ? 1 : Math.min(1, Math.min(1.40 / (aligned.width() * sourceScale),
            Math.min(0.58 / (aligned.height() * sourceScale), 0.38 / (aligned.depth() * sourceScale))));
        float scale = (float)(sourceScale*fit);
        Box scaled = new Box(raw).scale(scale);
        Model model = new Model("AD_Item_"+item.getId(), scale, Map.of(), new ModelAttachment[0], scaled,
            item.getModel(), item.getTexture(), null, null, 0,0,0,0, Map.of(), null,null,null,null,null,Map.of(),null,null);
        Vector3d center = new Vector3d(raw.middleX(),raw.middleY(),raw.middleZ()).mul(scale);
        rotation.transform(center);
        if (rack) {
            // A blade or stock can extend far to one side of what the grip actually holds.
            double gripX = rotation.transform(new Vector3d(geometry.grip())).x;
            double sectionX = sliceCenterX(geometry.shapes(), rotation, (center.y + RACK_GRIP_OFFSET) / scale, gripX);
            if (!Double.isFinite(sectionX)) {
                sectionX = sliceCenterX(geometry.shapes(), rotation, center.y / scale, gripX);
            }
            if (Double.isFinite(sectionX)) center.x = sectionX * scale;
        }
        return new Placement(model, rotation, center, aligned.depth() * scale / 2);
    }

    private static double sliceCenterX(List<Matrix4d> shapes, Rotation3f rotation, double height, double gripX) {
        List<GripSection> sections = new ArrayList<>();
        Vector3d[] corners = new Vector3d[8];
        for (int i = 0; i < corners.length; i++) corners[i] = new Vector3d();
        for (Matrix4d shape : shapes) {
            double minY = Double.POSITIVE_INFINITY;
            double maxY = Double.NEGATIVE_INFINITY;
            for (int i = 0; i < corners.length; i++) {
                rotation.transform(transformCorner(shape, i, corners[i]));
                minY = Math.min(minY, corners[i].y);
                maxY = Math.max(maxY, corners[i].y);
            }
            if (height < minY - 1e-9 || height > maxY + 1e-9) continue;
            double minX = Double.POSITIVE_INFINITY;
            double maxX = Double.NEGATIVE_INFINITY;
            for (int i = 0; i < corners.length; i++) {
                Vector3d a = corners[i];
                if (Math.abs(a.y - height) < 1e-9) {
                    minX = Math.min(minX, a.x);
                    maxX = Math.max(maxX, a.x);
                }
                // Adjacent vertices differ by one bit. Intersect each edge once.
                for (int bit = 1; bit < corners.length; bit <<= 1) {
                    if ((i & bit) != 0) continue;
                    Vector3d b = corners[i | bit];
                    if (height > Math.min(a.y, b.y) && height < Math.max(a.y, b.y)) {
                        double sectionX = a.x + (b.x - a.x) * (height - a.y) / (b.y - a.y);
                        minX = Math.min(minX, sectionX);
                        maxX = Math.max(maxX, sectionX);
                    }
                }
            }
            sections.add(new GripSection(minX, maxX));
        }
        if (sections.isEmpty()) return Double.NaN;
        sections.sort(Comparator.comparingDouble(GripSection::minX));
        GripSection group = sections.getFirst();
        GripSection nearest = group;
        double distance = Double.POSITIVE_INFINITY;
        for (int i = 1; i < sections.size(); i++) {
            GripSection next = sections.get(i);
            if (next.minX() <= group.maxX() + 1.0 / 64) {
                group = group.merge(next);
            } else {
                if (group.distanceTo(gripX) < distance) {
                    nearest = group;
                    distance = group.distanceTo(gripX);
                }
                group = next;
            }
        }
        // The handle distinguishes the shaft from a hooked blade crossing the same height.
        if (group.distanceTo(gripX) < distance) nearest = group;
        return (nearest.minX() + nearest.maxX()) / 2;
    }

    /** Entity models use 64 pixels per world unit (block furniture uses 32). */
    public static Box measure(byte[] blob) {
        return measureGeometry(blob).bounds();
    }
    private static Geometry measureGeometry(byte[] blob) {
        if (blob.length > 8_000_000) throw new IllegalArgumentException("Display model too large");
        JsonObject root = JsonParser.parseString(new String(blob,StandardCharsets.UTF_8)).getAsJsonObject();
        Box box = new Box().setEmpty();
        List<Matrix4d> shapes = new ArrayList<>();
        Vector3d grip = new Vector3d(Double.NaN);
        int[] count = {0};
        walk(root.getAsJsonArray("nodes"),new Matrix4d(),box,shapes,grip,0,count);
        if (!box.min.isFinite() || !box.max.isFinite() || box.width()+box.height()+box.depth() <= 0)
            throw new IllegalArgumentException("Display model has no visible geometry");
        if (!grip.isFinite()) grip.set(box.middleX(), box.middleY(), box.middleZ());
        return new Geometry(box, List.copyOf(shapes), grip);
    }
    private static Vector3d transformCorner(Matrix4d shape, int index, Vector3d dest) {
        dest.set((index & 1) == 0 ? -1 : 1, (index & 2) == 0 ? -1 : 1, (index & 4) == 0 ? -1 : 1);
        return shape.transformPosition(dest);
    }
    private static void walk(JsonArray nodes, Matrix4d parent, Box bounds, List<Matrix4d> shapes, Vector3d grip, int depth, int[] count) {
        if (nodes == null) return;
        if (depth > 64) throw new IllegalArgumentException("Display model nesting limit");
        for (JsonElement element:nodes) {
            if (++count[0] > 20000) throw new IllegalArgumentException("Display model node limit");
            JsonObject node=element.getAsJsonObject();
            Vector3d p=vector(node.getAsJsonObject("position"),0).div(64);
            JsonObject r=node.getAsJsonObject("orientation");
            Quaterniond q=r==null?new Quaterniond():new Quaterniond(number(r,"x",0),number(r,"y",0),number(r,"z",0),number(r,"w",1)).normalize();
            Matrix4d transform=new Matrix4d(parent).translate(p).rotate(q);
            if (!grip.isFinite() && node.has("name") && "Handle".equals(node.get("name").getAsString())) {
                transform.getTranslation(grip);
            }
            JsonObject shape=node.getAsJsonObject("shape");
            if (shape!=null && (!shape.has("visible") || shape.get("visible").getAsBoolean())) {
                String type=shape.has("type")?shape.get("type").getAsString():"none";
                if ("box".equals(type) || "quad".equals(type)) {
                    JsonObject settings=shape.getAsJsonObject("settings");
                    Vector3d size=vector(settings==null?null:settings.getAsJsonObject("size"),0);
                    if ("quad".equals(type) && settings!=null) {
                        String normal=settings.has("normal")?settings.get("normal").getAsString():"+Z";
                        if (normal.endsWith("X")) size.set(0,size.y,size.x);
                        else if (normal.endsWith("Y")) size.set(size.x,0,size.y);
                    }
                    size.mul(vector(shape.getAsJsonObject("stretch"),1)).div(128);
                    Vector3d offset=vector(shape.getAsJsonObject("offset"),0).div(64);
                    Matrix4d modelShape = new Matrix4d(transform).translate(offset).scale(size);
                    shapes.add(modelShape);
                    Vector3d corner = new Vector3d();
                    for (int i = 0; i < 8; i++) {
                        transformCorner(modelShape, i, corner);
                        bounds.min.min(corner);bounds.max.max(corner);
                    }
                }
            }
            walk(node.getAsJsonArray("children"),transform,bounds,shapes,grip,depth+1,count);
        }
    }
    private static double number(JsonObject object,String name,double fallback) {
        return object!=null && object.has(name)?object.get(name).getAsDouble():fallback;
    }
    private static Vector3d vector(JsonObject object,double fallback) {
        return new Vector3d(number(object,"x",fallback),number(object,"y",fallback),number(object,"z",fallback));
    }
}
