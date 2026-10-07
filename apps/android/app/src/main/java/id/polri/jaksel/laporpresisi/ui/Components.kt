package id.polri.jaksel.laporpresisi.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.Dp
import id.polri.jaksel.laporpresisi.R
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Komponen bersama ketiga layar — satu tempat untuk mengubah rupa seluruh aplikasi.
 * (Pengganti `box_field`, `box_critical`, `FieldLabel`, dan `OutlineButton` pada XML lama.)
 */

private val BoxShape = RoundedCornerShape(14.dp)
private val ButtonShape = RoundedCornerShape(12.dp)

/** Label huruf kapital kecil di atas isian atau bagian. */
@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier, icon: ImageVector? = null) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        if (icon != null) {
            Icon(icon, contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(6.dp))
        }
        Text(text.uppercase(), style = MaterialTheme.typography.labelSmall)
    }
}

/** Kotak bergaris tipis: wadah isian, kartu, dan panel. */
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

/** Kotak bergaris merah: darurat dan imbauan. */
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
    icon: ImageVector? = null,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        shape = ButtonShape,
        colors = ButtonDefaults.buttonColors(
            containerColor = PresisiColors.Accent,
            contentColor = PresisiColors.Base950,
            disabledContainerColor = PresisiColors.Base700,
            disabledContentColor = PresisiColors.InkFaint,
        ),
        modifier = modifier.fillMaxWidth().height(52.dp),
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(10.dp))
        }
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
    icon: ImageVector? = null,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        shape = ButtonShape,
        border = BorderStroke(1.dp, if (enabled) PresisiColors.Base700 else PresisiColors.Base800),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = PresisiColors.Base900,
            contentColor = PresisiColors.Accent,
            disabledContentColor = PresisiColors.InkFaint,
        ),
        modifier = (if (fullWidth) modifier.fillMaxWidth() else modifier).height(48.dp),
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
        }
        Text(text, fontSize = 14.sp)
    }
}

/** Keterangan kecil di bawah tombol atau isian. */
@Composable
fun Hint(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.bodySmall, modifier = modifier)
}

// ---------------------------------------------------------------------------------
// Isian formulir
// ---------------------------------------------------------------------------------

/** Warna isian teks yang seragam: kotak biru malam bergaris tipis, aksen saat fokus. */
@Composable
fun fieldColors() = androidx.compose.material3.OutlinedTextFieldDefaults.colors(
    focusedTextColor = PresisiColors.Ink,
    unfocusedTextColor = PresisiColors.Ink,
    disabledTextColor = PresisiColors.InkFaint,
    focusedContainerColor = PresisiColors.Base900,
    unfocusedContainerColor = PresisiColors.Base900,
    disabledContainerColor = PresisiColors.Base900,
    cursorColor = PresisiColors.Accent,
    focusedBorderColor = PresisiColors.Accent,
    unfocusedBorderColor = PresisiColors.Base700,
    disabledBorderColor = PresisiColors.Base800,
    focusedPlaceholderColor = PresisiColors.InkFaint,
    unfocusedPlaceholderColor = PresisiColors.InkFaint,
    focusedTrailingIconColor = PresisiColors.InkMuted,
    unfocusedTrailingIconColor = PresisiColors.InkMuted,
)

/** Isian teks berlabel. [minLines] > 1 menjadikannya area teks. */
@Composable
fun InputField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    minLines: Int = 1,
    maxLength: Int = Int.MAX_VALUE,
    password: Boolean = false,
    keyboardOptions: androidx.compose.foundation.text.KeyboardOptions =
        androidx.compose.foundation.text.KeyboardOptions.Default,
) {
    Column(modifier.fillMaxWidth()) {
        SectionLabel(label, Modifier.padding(top = 14.dp, bottom = 4.dp))
        androidx.compose.material3.OutlinedTextField(
            value = value,
            onValueChange = { if (it.length <= maxLength) onValueChange(it) },
            placeholder = placeholder?.let { { Text(it, style = MaterialTheme.typography.bodyMedium) } },
            minLines = minLines,
            singleLine = minLines == 1,
            shape = BoxShape,
            colors = fieldColors(),
            textStyle = MaterialTheme.typography.bodyLarge,
            keyboardOptions = keyboardOptions,
            visualTransformation = if (password) {
                androidx.compose.ui.text.input.PasswordVisualTransformation()
            } else {
                androidx.compose.ui.text.input.VisualTransformation.None
            },
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

/**
 * Pemilih satu nilai dari daftar (pengganti `Spinner`). Nilainya selalu salah satu dari
 * [options] — tidak ada isian bebas — supaya yang terkirim cocok dengan master di server.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun Picker(
    label: String,
    value: String,
    options: List<String>,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String = "Pilih",
    enabled: Boolean = true,
) {
    var open by remember { mutableStateOf(false) }
    Column(modifier.fillMaxWidth()) {
        SectionLabel(label, Modifier.padding(top = 14.dp, bottom = 4.dp))
        ExposedDropdownMenuBox(
            expanded = open && enabled,
            onExpandedChange = { if (enabled) open = !open },
        ) {
            androidx.compose.material3.OutlinedTextField(
                value = value.ifBlank { placeholder },
                onValueChange = {},
                readOnly = true,
                enabled = enabled,
                singleLine = true,
                shape = BoxShape,
                colors = fieldColors(),
                textStyle = MaterialTheme.typography.bodyLarge.copy(
                    color = if (value.isBlank()) PresisiColors.InkFaint else PresisiColors.Ink,
                ),
                trailingIcon = {
                    ExposedDropdownMenuDefaults.TrailingIcon(expanded = open)
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor(),
            )
            ExposedDropdownMenu(
                expanded = open && enabled,
                onDismissRequest = { open = false },
                modifier = Modifier.background(PresisiColors.Base800),
            ) {
                for (option in options) {
                    DropdownMenuItem(
                        text = { Text(option, color = PresisiColors.Ink) },
                        onClick = {
                            onSelect(option)
                            open = false
                        },
                    )
                }
            }
        }
    }
}

/** Pesan galat dalam kotak bergaris merah; tidak digambar bila `null`. */
@Composable
fun ErrorBox(message: String?, modifier: Modifier = Modifier) {
    if (message == null) return
    CriticalPanel(modifier) {
        Text(message, color = PresisiColors.Critical, fontSize = 12.sp, lineHeight = 18.sp)
    }
}

/** Lambang PRESISI (perisai + sasaran), dari `res/drawable/ic_logo.xml`. */
@Composable
fun BrandMark(size: Dp, modifier: Modifier = Modifier) {
    Image(
        painterResource(R.drawable.ic_logo),
        contentDescription = null,
        modifier = modifier.size(size),
    )
}

/**
 * Kepala layar: lambang, nama aplikasi, dan satuan.
 *
 * [compact] = satu baris kecil untuk layar isian; selain itu lambang besar di tengah
 * untuk layar muka.
 */
@Composable
fun BrandHeader(title: String, subtitle: String, compact: Boolean = false, modifier: Modifier = Modifier) {
    if (compact) {
        Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            BrandMark(36.dp)
            Spacer(Modifier.width(12.dp))
            Column {
                Text(title, style = MaterialTheme.typography.titleMedium, fontSize = 18.sp, letterSpacing = 2.sp)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = PresisiColors.InkMuted)
            }
        }
    } else {
        Column(modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            BrandMark(96.dp)
            Text(
                title,
                style = MaterialTheme.typography.headlineMedium,
                letterSpacing = 4.sp,
                modifier = Modifier.padding(top = 12.dp),
            )
            Text(
                subtitle.uppercase(),
                fontSize = 11.sp,
                letterSpacing = 2.sp,
                color = PresisiColors.InkMuted,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}
