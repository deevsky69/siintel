package id.polri.jaksel.laporpresisi

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AreaNearestTest {
    private val areas = listOf(
        PublicApi.AreaOption(
            "Tebet",
            listOf(PublicApi.Kelurahan("Tebet Timur", -6.2286, 106.8542)),
        ),
        PublicApi.AreaOption(
            "Kebayoran Baru",
            listOf(
                PublicApi.Kelurahan("Senayan", -6.2270, 106.8003),
                PublicApi.Kelurahan("Gunung", -6.2390, 106.8010),
            ),
        ),
    )

    @Test
    fun `kelurahan terdekat dipilih lintas kecamatan`() {
        val nearest = AreaNearest.nearest(areas, -6.2380, 106.8020)
        assertEquals("Kebayoran Baru", nearest?.kecamatan)
        assertEquals("Gunung", nearest?.kelurahan)
        assertTrue(nearest!!.distanceM < 200.0)
    }

    @Test
    fun `tanpa daftar kelurahan tidak ada usulan`() {
        assertNull(AreaNearest.nearest(emptyList(), -6.2, 106.8))
    }

    @Test
    fun `jarak satu derajat lintang sekitar 111 km`() {
        val d = AreaNearest.distanceMeters(0.0, 0.0, 1.0, 0.0)
        assertTrue(d > 111_000 && d < 111_300)
    }
}
