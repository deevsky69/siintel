package id.polri.jaksel.laporpresisi.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * Palet PRESISI — mengikuti aplikasi web (dasar biru malam, aksen sian) supaya warga dan
 * petugas mengenali keduanya sebagai satu sistem. `res/values/colors.xml` menyimpan nilai
 * yang sama untuk tema jendela dan latar ikon peluncur; ubah keduanya bersama.
 *
 * Aplikasi selalu gelap, apa pun pengaturan ponsel: palet terang belum dirancang, dan
 * "terang seadanya" dari Material akan terlihat seperti aplikasi lain.
 */
object PresisiColors {
    val Base950 = Color(0xFF050B18)
    val Base900 = Color(0xFF0A1424)
    val Base800 = Color(0xFF132339)
    val Base700 = Color(0xFF1B2F4A)
    val Ink = Color(0xFFE6F0FF)
    val InkMuted = Color(0xFF8EA6C8)
    val InkFaint = Color(0xFF5B7796)
    val Accent = Color(0xFF22D3EE)
    val Critical = Color(0xFFEF4444)
    val Ok = Color(0xFF4ADE80)
    val Warning = Color(0xFFF59E0B)
}

private val ColorScheme = darkColorScheme(
    primary = PresisiColors.Accent,
    onPrimary = PresisiColors.Base950,
    secondary = PresisiColors.InkMuted,
    background = PresisiColors.Base950,
    onBackground = PresisiColors.Ink,
    surface = PresisiColors.Base900,
    onSurface = PresisiColors.Ink,
    surfaceVariant = PresisiColors.Base800,
    onSurfaceVariant = PresisiColors.InkMuted,
    outline = PresisiColors.Base700,
    error = PresisiColors.Critical,
    onError = PresisiColors.Ink,
)

private val Type = Typography(
    headlineMedium = TextStyle(fontSize = 26.sp, fontWeight = FontWeight.Bold, color = PresisiColors.Ink),
    titleMedium = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = PresisiColors.Ink),
    bodyLarge = TextStyle(fontSize = 15.sp, lineHeight = 22.sp, color = PresisiColors.Ink),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp, color = PresisiColors.InkMuted),
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 18.sp, color = PresisiColors.InkFaint),
    labelSmall = TextStyle(
        fontSize = 10.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 1.2.sp,
        color = PresisiColors.InkMuted,
    ),
)

@Composable
fun PresisiTheme(content: @Composable () -> Unit) {
    // Dibaca supaya pengubahan pengaturan ponsel tetap memicu komposisi ulang; nilainya
    // sengaja tidak dipakai — lihat catatan PresisiColors.
    isSystemInDarkTheme()
    MaterialTheme(colorScheme = ColorScheme, typography = Type, content = content)
}
