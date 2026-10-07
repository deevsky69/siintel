package id.polri.jaksel.laporpresisi

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.ui.CriticalPanel
import id.polri.jaksel.laporpresisi.ui.ErrorBox
import id.polri.jaksel.laporpresisi.ui.Hint
import id.polri.jaksel.laporpresisi.ui.InputField
import id.polri.jaksel.laporpresisi.ui.Panel
import id.polri.jaksel.laporpresisi.ui.Picker
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.ScreenHeader
import id.polri.jaksel.laporpresisi.ui.SecondaryButton
import id.polri.jaksel.laporpresisi.ui.SectionLabel

/** Titik yang dibagikan pelapor. */
data class SharedPoint(val latitude: Double, val longitude: Double, val accuracyM: Double?)

/** Satu lampiran yang sudah dititipkan, dengan nama berkasnya untuk ditampilkan. */
data class StagedFile(val staged: PublicApi.Staged, val name: String)

/**
 * Seluruh keadaan layar lapor. Tampilan ([LaporScreen]) hanya membaca ini; yang mengubahnya
 * adalah [LaporActivity] lewat callback [LaporActions]. Dipisah supaya layar dapat
 * dipratinjau di Android Studio pada tiap keadaannya — memuat, formulir, mengirim, tiket.
 */
data class LaporState(
    val options: PublicApi.Options? = null,
    val optionsFailed: Boolean = false,
    val category: String = "",
    val kecamatan: String = "",
    val kelurahan: String = "",
    val place: String = "",
    val story: String = "",
    val location: SharedPoint? = null,
    val locationBusy: Boolean = false,
    /** Catatan di bawah tombol lokasi; `null` berarti bunyi bawaan. */
    val locationNote: String? = null,
    /** Catatan di bawah pemilih kelurahan bila terisi otomatis dari lokasi. */
    val kelurahanSuggestion: String? = null,
    val attachments: List<StagedFile> = emptyList(),
    val uploading: Boolean = false,
    val error: String? = null,
    val sending: Boolean = false,
    val busy: Boolean = false,
    /** Nomor tiket setelah terkirim; selama `null` formulir yang tampil. */
    val ticket: String? = null,
) {
    val kelurahanOptions: List<String>
        get() = options?.detailedAreas
            ?.firstOrNull { it.kecamatan == kecamatan }
            ?.kelurahan?.map { it.name }
            .orEmpty()
}

class LaporActions(
    val onCategory: (String) -> Unit,
    val onKecamatan: (String) -> Unit,
    val onKelurahan: (String) -> Unit,
    val onPlace: (String) -> Unit,
    val onStory: (String) -> Unit,
    val onLocation: () -> Unit,
    val onPickFiles: () -> Unit,
    val onSend: () -> Unit,
    val onAgain: () -> Unit,
)

@Composable
fun LaporScreen(state: LaporState, actions: LaporActions) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Box(Modifier.fillMaxSize()) {
            Column(
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(20.dp),
            ) {
                ScreenHeader(stringResource(R.string.app_name), stringResource(R.string.subtitle))

                CriticalPanel(Modifier.padding(top = 18.dp)) {
                    Text(
                        stringResource(R.string.emergency_title),
                        color = PresisiColors.Critical,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                    )
                    Text(
                        stringResource(R.string.emergency_body),
                        style = MaterialTheme.typography.bodySmall,
                        color = PresisiColors.InkMuted,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }

                when {
                    state.ticket != null -> SentPanel(state.ticket, actions.onAgain)
                    state.optionsFailed -> ErrorBox(stringResource(R.string.err_options), Modifier.padding(top = 18.dp))
                    state.options != null -> ReportForm(state, actions)
                    else -> Hint(stringResource(R.string.loading_options), Modifier.padding(top = 18.dp))
                }
            }

            if (state.busy) {
                CircularProgressIndicator(
                    color = PresisiColors.Accent,
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(top = 8.dp),
                )
            }
        }
    }
}

@Composable
private fun ReportForm(state: LaporState, actions: LaporActions) {
    val options = state.options ?: return
    val skip = stringResource(R.string.kelurahan_skip)

    Column(Modifier.padding(top = 6.dp)) {
        Picker(
            label = stringResource(R.string.label_category),
            value = state.category,
            options = options.categories,
            onSelect = actions.onCategory,
            placeholder = "Pilih jenis kejadian",
        )
        Picker(
            label = stringResource(R.string.label_area),
            value = state.kecamatan,
            options = options.areas,
            onSelect = actions.onKecamatan,
            placeholder = "Pilih kecamatan",
        )
        // Pemilih kelurahan hanya bila server mengirim `areas` (5 Oktober 2026); server
        // lama tidak punya daftarnya dan laporan sebatas kecamatan tetap sah.
        if (state.kelurahanOptions.isNotEmpty()) {
            Picker(
                label = stringResource(R.string.label_kelurahan),
                value = state.kelurahan,
                options = listOf(skip) + state.kelurahanOptions,
                onSelect = { actions.onKelurahan(if (it == skip) "" else it) },
                placeholder = skip,
            )
            Hint(
                state.kelurahanSuggestion ?: stringResource(R.string.kelurahan_note),
                Modifier.padding(top = 4.dp),
            )
        }
        InputField(
            label = stringResource(R.string.label_place),
            value = state.place,
            onValueChange = actions.onPlace,
            placeholder = stringResource(R.string.hint_place),
            maxLength = 255,
        )
        InputField(
            label = stringResource(R.string.label_story),
            value = state.story,
            onValueChange = actions.onStory,
            placeholder = stringResource(R.string.hint_story),
            minLines = 4,
            maxLength = 1000,
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
        )
        Hint(stringResource(R.string.privacy_warning), Modifier.padding(top = 6.dp))

        // ----- Lokasi -----
        SectionLabel(stringResource(R.string.label_location), Modifier.padding(top = 16.dp))
        state.location?.let { point ->
            Text(
                String.format(
                    java.util.Locale.US,
                    "%.5f, %.5f (±%.0f m)",
                    point.latitude,
                    point.longitude,
                    point.accuracyM ?: 0.0,
                ),
                style = MaterialTheme.typography.bodyLarge,
                fontFamily = FontFamily.Monospace,
                fontSize = 13.sp,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
        SecondaryButton(
            text = stringResource(
                when {
                    state.locationBusy -> R.string.sharing_location
                    state.location != null -> R.string.clear_location
                    else -> R.string.share_location
                },
            ),
            onClick = actions.onLocation,
            enabled = !state.locationBusy,
            fullWidth = false,
            modifier = Modifier.padding(top = 6.dp),
        )
        Hint(state.locationNote ?: stringResource(R.string.location_note), Modifier.padding(top = 6.dp))

        // ----- Lampiran -----
        SectionLabel(stringResource(R.string.label_attachments), Modifier.padding(top = 16.dp))
        if (state.attachments.isNotEmpty()) {
            Text(
                state.attachments.joinToString("\n") { "• ${it.name} — ${maxOf(1L, it.staged.byteSize / 1024)} KB" },
                style = MaterialTheme.typography.bodyLarge,
                fontSize = 13.sp,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
        val full = options.maxAttachments > 0 && state.attachments.size >= options.maxAttachments
        SecondaryButton(
            text = stringResource(
                when {
                    state.uploading -> R.string.uploading
                    full -> R.string.attachments_full
                    else -> R.string.pick_file
                },
            ),
            onClick = actions.onPickFiles,
            enabled = !state.uploading && !full,
            fullWidth = false,
            modifier = Modifier.padding(top = 6.dp),
        )
        Hint(stringResource(R.string.attachment_note), Modifier.padding(top = 6.dp))

        ErrorBox(state.error, Modifier.padding(top = 12.dp))

        PrimaryButton(
            text = stringResource(if (state.sending) R.string.sending else R.string.send),
            onClick = actions.onSend,
            enabled = !state.sending,
            modifier = Modifier.padding(top = 16.dp),
        )
        Hint(stringResource(R.string.no_identity), Modifier.padding(top = 14.dp))
        Hint(stringResource(R.string.coord_note), Modifier.padding(top = 6.dp))
    }
}

/**
 * Tiket setelah laporan tercatat. Kode klaim TIDAK ditampilkan: aplikasi menyimpannya
 * terenkripsi dan memakainya sendiri; yang perlu diingat pelapor cukup nomor tiketnya.
 */
@Composable
private fun SentPanel(ticket: String, onAgain: () -> Unit) {
    Panel(Modifier.padding(top = 28.dp)) {
        Column(Modifier.fillMaxWidth().padding(10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                stringResource(R.string.sent_title).uppercase(),
                color = PresisiColors.Accent,
                fontWeight = FontWeight.Bold,
                fontSize = 11.sp,
                letterSpacing = 1.2.sp,
            )
            Text(
                stringResource(R.string.ticket_label),
                style = MaterialTheme.typography.bodySmall,
                color = PresisiColors.InkMuted,
                modifier = Modifier.padding(top = 14.dp),
            )
            Text(
                ticket,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                fontSize = 26.sp,
                letterSpacing = 2.sp,
                color = PresisiColors.Ink,
                modifier = Modifier.padding(top = 4.dp),
            )
            Text(
                stringResource(R.string.sent_body),
                style = MaterialTheme.typography.bodySmall,
                color = PresisiColors.InkMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 16.dp),
            )
            Spacer(Modifier.height(20.dp))
            PrimaryButton(stringResource(R.string.send_another), onClick = onAgain)
        }
    }
}

private val PREVIEW_OPTIONS = PublicApi.Options(
    categories = listOf("Pencurian kendaraan", "Pencurian dengan pemberatan", "Lainnya"),
    areas = listOf("Tebet", "Kebayoran Baru"),
    detailedAreas = listOf(
        PublicApi.AreaOption("Tebet", listOf(PublicApi.Kelurahan("Tebet Timur", -6.2286, 106.8542))),
    ),
    coordinateBasis = "",
    attachmentBasis = "",
    maxAttachments = 3,
    maxAttachmentBytes = 26_214_400,
)

private val NO_ACTIONS = LaporActions({}, {}, {}, {}, {}, {}, {}, {}, {})

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 1400)
@Composable
private fun FormPreview() {
    PresisiTheme {
        LaporScreen(
            LaporState(
                options = PREVIEW_OPTIONS,
                category = "Pencurian kendaraan",
                kecamatan = "Tebet",
                kelurahan = "Tebet Timur",
                kelurahanSuggestion = "Terisi otomatis dari lokasi Anda: Tebet Timur (sekitar 180 m).",
                location = SharedPoint(-6.2286, 106.8542, 25.0),
                attachments = listOf(StagedFile(PublicApi.Staged("h1", "image", 420_000), "foto.jpg")),
                error = "Contoh pesan galat.",
            ),
            NO_ACTIONS,
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 640)
@Composable
private fun SentPreview() {
    PresisiTheme { LaporScreen(LaporState(options = PREVIEW_OPTIONS, ticket = "CR-2026-0042"), NO_ACTIONS) }
}
