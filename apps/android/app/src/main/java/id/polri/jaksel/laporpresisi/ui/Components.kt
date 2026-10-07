package id.polri.jaksel.laporpresisi.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Komponen bersama ketiga layar. Padanan `box_field`, `box_critical`, `FieldLabel`, dan
 * `OutlineButton` pada XML — satu tempat untuk mengubah rupa seluruh aplikasi.
 */

private val BoxShape = RoundedCornerShape(8.dp)

/** Label huruf kapital kecil di atas isian atau bagian. */
@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, modifier = modifier)
}

/** Kotak bergaris tipis (`box_field`): wadah isian, kartu, dan panel. */
@Composable
fun Panel(
    modifier: Modifier = Modifier,
    borderColor: Color = PresisiColors.Base700,
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .fillMaxWidth()
            .background(PresisiColors.Base900, BoxShape)
            .border(1.dp, borderColor, BoxShape)
            .padding(14.dp),
        content = content,
    )
}

/** Kotak bergaris merah (`box_critical`): darurat dan imbauan. */
@Composable
fun CriticalPanel(modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) =
    Panel(modifier, borderColor = PresisiColors.Critical, content = content)

/** Tombol utama — satu per layar, berisi aksen. */
@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        shape = BoxShape,
        colors = ButtonDefaults.buttonColors(
            containerColor = PresisiColors.Accent,
            contentColor = PresisiColors.Base950,
            disabledContainerColor = PresisiColors.Base700,
            disabledContentColor = PresisiColors.InkFaint,
        ),
        modifier = modifier.fillMaxWidth().height(52.dp),
    ) {
        Text(text, fontSize = 15.sp, fontWeight = FontWeight.Bold)
    }
}

/** Tombol garis luar — aksi kedua. */
@Composable
fun SecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    fullWidth: Boolean = true,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        shape = BoxShape,
        border = BorderStroke(1.dp, if (enabled) PresisiColors.Base700 else PresisiColors.Base800),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = PresisiColors.Base900,
            contentColor = PresisiColors.Accent,
            disabledContentColor = PresisiColors.InkFaint,
        ),
        modifier = (if (fullWidth) modifier.fillMaxWidth() else modifier).height(48.dp),
    ) {
        Text(text, fontSize = 14.sp)
    }
}

/** Keterangan kecil di bawah tombol atau isian. */
@Composable
fun Hint(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.bodySmall, modifier = modifier)
}
