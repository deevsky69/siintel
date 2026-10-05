package id.polri.jaksel.laporpresisi

import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Kelurahan terdekat dari sebuah titik — murni, tanpa Android, supaya dapat diuji di JVM.
 *
 * Padanan `apps/web/src/app/(publik)/lapor/area-nearest.ts`. Hasilnya USULAN yang dapat
 * dikoreksi pelapor: lokasi jaringan bisa meleset ratusan meter. Server mengulang pencarian
 * yang sama dengan PostGIS bila kelurahan tidak dikirim.
 */
object AreaNearest {
    private const val EARTH_RADIUS_M = 6_371_000.0

    data class Nearest(val kecamatan: String, val kelurahan: String, val distanceM: Double)

    fun distanceMeters(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLng = Math.toRadians(lng2 - lng1)
        val h = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLng / 2) * sin(dLng / 2)
        return 2 * EARTH_RADIUS_M * asin(sqrt(h))
    }

    fun nearest(areas: List<PublicApi.AreaOption>, latitude: Double, longitude: Double): Nearest? {
        var best: Nearest? = null
        for (area in areas) {
            for (kel in area.kelurahan) {
                val d = distanceMeters(latitude, longitude, kel.latitude, kel.longitude)
                if (best == null || d < best.distanceM) {
                    best = Nearest(area.kecamatan, kel.name, d)
                }
            }
        }
        return best
    }
}
