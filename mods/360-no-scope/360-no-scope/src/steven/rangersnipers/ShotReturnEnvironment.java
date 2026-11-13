package steven.rangersnipers;

import com.hypixel.hytale.math.util.ChunkUtil;
import com.hypixel.hytale.server.core.universe.world.chunk.heightmap.HeightmapColumn;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import org.joml.Vector3dc;

/** Estimates sky exposure at the original muzzle, using resident column data only. */
final class ShotReturnEnvironment {
    private static final int SAMPLE_OFFSET = 2;

    private ShotReturnEnvironment() { }

    static boolean openSky(ChunkStore chunks, Vector3dc muzzle) {
        if (!Double.isFinite(muzzle.x()) || !Double.isFinite(muzzle.y()) || !Double.isFinite(muzzle.z())
            || !safeBlockCoordinate(muzzle.x()) || !safeBlockCoordinate(muzzle.z())) return false;
        int x = (int) Math.floor(muzzle.x());
        int y = (int) Math.floor(muzzle.y());
        int z = (int) Math.floor(muzzle.z());
        int centre = top(chunks, x, z);
        if (centre == HeightmapColumn.NO_HEIGHT || centre >= y) return false;

        int east = top(chunks, x + SAMPLE_OFFSET, z);
        int west = top(chunks, x - SAMPLE_OFFSET, z);
        int south = top(chunks, x, z + SAMPLE_OFFSET);
        int north = top(chunks, x, z - SAMPLE_OFFSET);
        if (east == HeightmapColumn.NO_HEIGHT || west == HeightmapColumn.NO_HEIGHT
            || south == HeightmapColumn.NO_HEIGHT || north == HeightmapColumn.NO_HEIGHT) return false;

        int open = 1;
        if (east < y) open++;
        if (west < y) open++;
        if (south < y) open++;
        if (north < y) open++;
        return open >= 3;
    }

    private static boolean safeBlockCoordinate(double coordinate) {
        return coordinate >= Integer.MIN_VALUE + SAMPLE_OFFSET && coordinate <= Integer.MAX_VALUE - SAMPLE_OFFSET;
    }

    private static int top(ChunkStore chunks, int x, int z) {
        long column = ChunkUtil.indexChunkFromBlock(x, z);
        var heightmap = chunks.getChunkComponent(column, HeightmapColumn.getComponentType());
        if (heightmap == null || heightmap.getHeightmap() == null) return HeightmapColumn.NO_HEIGHT;
        int localX = x & ChunkUtil.SIZE_MINUS_1;
        int localZ = z & ChunkUtil.SIZE_MINUS_1;
        // Collision tops catch solid transparent roofs in modern heightmaps.
        return Math.max(heightmap.getHeight(localX, localZ), heightmap.getCollisionHeight(localX, localZ));
    }
}
