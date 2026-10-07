package id.polri.jaksel.laporpresisi

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.ui.CriticalPanel
import id.polri.jaksel.laporpresisi.ui.Hint
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.SecondaryButton
import id.polri.jaksel.laporpresisi.ui.SectionLabel

/**
 * Isi layar muka. Murni tampilan: seluruh data datang lewat [state], seluruh aksi keluar
 * lewat callback — supaya dapat dipratinjau di Android Studio tanpa jaringan dan tanpa
 * Activity. Alasan susunannya (imbauan SEBELUM tombol lapor, 110 di atas segalanya, tombol
 * status hanya bila pernah melapor) ada pada dokumentasi [MainActivity].
 */
data class HomeState(
    val alerts: List<PublicApi.Imbauan> = emptyList(),
    val hasTicket: Boolean = false,
    /** Hasil cek status; `null` berarti belum ditekan. */
    val statusResult: String? = null,
    val version: String = "",
)

@Composable
fun HomeScreen(
    state: HomeState,
    onReport: () -> Unit,
    onOfficer: () -> Unit,
    onCheckStatus: () -> Unit,
) {
    Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineMedium)
                Text(
                    stringResource(R.string.subtitle).uppercase(),
                    fontSize = 12.sp,
                    letterSpacing = 2.sp,
                    color = PresisiColors.InkMuted,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }

            Text(
                stringResource(R.string.home_lead),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 20.dp),
            )

            CriticalPanel(Modifier.padding(top = 20.dp)) {
                Text(
                    stringResource(R.string.emergency_title),
                    color = PresisiColors.Critical,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                )
            }

            if (state.alerts.isNotEmpty()) {
                Spacer(Modifier.height(20.dp))
                SectionLabel(stringResource(R.string.home_alerts_title))
                for (row in state.alerts) {
                    AlertCard(row, Modifier.padding(top = 8.dp))
                }
                Hint(stringResource(R.string.home_alerts_basis), Modifier.padding(top = 8.dp))
            }

            Spacer(Modifier.height(26.dp))
            PrimaryButton(stringResource(R.string.home_report), onClick = onReport)
            Hint(stringResource(R.string.home_report_hint), Modifier.padding(top = 8.dp))

            if (state.hasTicket) {
                Spacer(Modifier.height(12.dp))
                SecondaryButton(stringResource(R.string.home_status), onClick = onCheckStatus)
                state.statusResult?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodyMedium,
                        fontSize = 13.sp,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
            }

            Spacer(Modifier.height(24.dp))
            SecondaryButton(stringResource(R.string.home_officer), onClick = onOfficer)
            Hint(stringResource(R.string.home_officer_hint), Modifier.padding(top = 8.dp))

            Text(
                "${stringResource(R.string.version_label)} ${state.version}",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier
                    .padding(top = 32.dp)
                    .align(Alignment.CenterHorizontally),
            )
        }
    }
}

/**
 * Satu imbauan. Sengaja tanpa aksi klik: imbauan adalah kanal SATU ARAH, dan rincian yang
 * ada di sistem justru yang tidak boleh keluar.
 */
@Composable
private fun AlertCard(row: PublicApi.Imbauan, modifier: Modifier = Modifier) {
    val jam = row.timeWindow?.let { " · $it WIB" } ?: ""
    CriticalPanel(modifier) {
        Text(
            "${row.threatType} · ${row.areaText}$jam",
            color = PresisiColors.Critical,
            fontWeight = FontWeight.Bold,
            fontSize = 13.sp,
        )
        Text(
            row.message,
            style = MaterialTheme.typography.bodyMedium,
            fontSize = 13.sp,
            modifier = Modifier.padding(top = 4.dp),
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 780)
@Composable
private fun HomePreview() {
    PresisiTheme {
        HomeScreen(
            state = HomeState(
                alerts = listOf(
                    PublicApi.Imbauan(
                        code = "PAL-0026",
                        threatType = "CURANMOR",
                        areaText = "Kecamatan Tebet",
                        timeWindow = "18:00-23:59",
                        message = "Imbauan kewaspadaan. Kunci ganda kendaraan Anda dan parkir di tempat terang.",
                    ),
                ),
                hasTicket = true,
                statusResult = "CR-2026-0001 · Diverifikasi\nDiputuskan petugas triase.",
                version = "2.2.0",
            ),
            onReport = {},
            onOfficer = {},
            onCheckStatus = {},
        )
    }
}
