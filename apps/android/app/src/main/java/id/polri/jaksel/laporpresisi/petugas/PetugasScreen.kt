package id.polri.jaksel.laporpresisi.petugas

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.ExitToApp
import androidx.compose.material.icons.automirrored.outlined.List
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.DateRange
import androidx.compose.material.icons.outlined.Done
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Place
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Star
import androidx.compose.material.icons.outlined.ThumbUp
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import id.polri.jaksel.laporpresisi.R
import id.polri.jaksel.laporpresisi.ui.BrandHeader
import id.polri.jaksel.laporpresisi.ui.CountPill
import id.polri.jaksel.laporpresisi.ui.ErrorBox
import id.polri.jaksel.laporpresisi.ui.Hint
import id.polri.jaksel.laporpresisi.ui.InputField
import id.polri.jaksel.laporpresisi.ui.Panel
import id.polri.jaksel.laporpresisi.ui.PresisiColors
import id.polri.jaksel.laporpresisi.ui.PresisiTheme
import id.polri.jaksel.laporpresisi.ui.PrimaryButton
import id.polri.jaksel.laporpresisi.ui.ScreenScaffold
import id.polri.jaksel.laporpresisi.ui.SecondaryButton
import id.polri.jaksel.laporpresisi.ui.SectionLabel
import id.polri.jaksel.laporpresisi.ui.StatChip

/** Nilai `kind` dari `GET /notifications` untuk antrean laporan warga. */
const val KIND_CITIZEN_REPORT = "CITIZEN_REPORT"

/** Nama permission persis seperti `config/rbac/permissions.yaml`; server yang menegakkannya. */
object Perm {
    const val WARNING_READ = "warning:read"
    const val WARNING_ACK = "warning:acknowledge"
    const val WARNING_RESOLVE = "warning:resolve"
    const val REPORT_READ = "citizen_report:read"
    const val REPORT_WRITE = "citizen_report:write"
    const val RECOMMENDATION_READ = "recommendation:read"
    const val DECIDE = "commander_decision:approve"
}

/** Menu bawah. Yang tampil bergantung permission dari `/auth/me`; ANTREAN dan AKUN selalu. */
enum class Tab(val label: Int, val icon: ImageVector, val requires: String?) {
    ANTREAN(R.string.tab_queue, Icons.Outlined.Notifications, null),
    PERINGATAN(R.string.tab_warnings, Icons.Outlined.Warning, Perm.WARNING_READ),
    LAPORAN(R.string.tab_reports, Icons.Outlined.Edit, Perm.REPORT_READ),
    REKOMENDASI(R.string.tab_recommendations, Icons.Outlined.ThumbUp, Perm.RECOMMENDATION_READ),
    AKUN(R.string.tab_account, Icons.Outlined.AccountCircle, null),
}

/** Satu rincian yang sedang dibuka: tab asalnya dan kodenya. */
data class DetailRef(val tab: Tab, val code: String)

data class PetugasState(
    val username: String = "",
    val password: String = "",
    val signingIn: Boolean = false,
    val loginError: String? = null,
    val profile: Api.Profile? = null,
    val feed: Api.Feed? = null,
    /** Pesan di bawah antrean: galat pemuatan atau kabar tindakan; `null` = bunyi bawaan. */
    val note: String? = null,
    /** Kode yang sedang ditindak (verifikasi/terima/selesaikan/putuskan); tombolnya dimatikan. */
    val acting: Set<String> = emptySet(),
    val busy: Boolean = false,
    val version: String = "",
    val tab: Tab = Tab.ANTREAN,
    val detail: DetailRef? = null,
    val warnings: List<Api.Warning>? = null,
    val reports: List<Api.Report>? = null,
    val recommendations: List<Api.Recommendation>? = null,
    val decisionChoice: String = "APPROVED",
    val decisionReason: String = "",
    val decisionText: String = "",
) {
    fun allows(permission: String): Boolean = profile?.permissions?.contains(permission) == true
    val tabs: List<Tab> get() = Tab.entries.filter { it.requires == null || allows(it.requires) }
}

class PetugasActions(
    val onUsername: (String) -> Unit,
    val onPassword: (String) -> Unit,
    val onSignIn: () -> Unit,
    val onRefresh: () -> Unit,
    val onSignOut: () -> Unit,
    val onTab: (Tab) -> Unit,
    val onOpen: (DetailRef) -> Unit,
    val onBack: () -> Unit,
    val onVerify: (String) -> Unit,
    val onAcknowledge: (String) -> Unit,
    val onResolve: (String) -> Unit,
    val onDecisionChoice: (String) -> Unit,
    val onDecisionReason: (String) -> Unit,
    val onDecisionText: (String) -> Unit,
    val onDecide: (String) -> Unit,
)

private data class RoleLook(val icon: ImageVector, val tagline: Int)

private fun roleLook(role: String): RoleLook = when (role.lowercase()) {
    "pimpinan" -> RoleLook(Icons.Outlined.Star, R.string.role_pimpinan)
    "polsek" -> RoleLook(Icons.Outlined.Place, R.string.role_polsek)
    "fungsi" -> RoleLook(Icons.Outlined.Build, R.string.role_fungsi)
    "administrator" -> RoleLook(Icons.Outlined.Settings, R.string.role_admin)
    else -> RoleLook(Icons.Outlined.Person, R.string.role_admin)
}

private fun kindIcon(kind: String): ImageVector = when (kind) {
    "WARNING" -> Icons.Outlined.Warning
    KIND_CITIZEN_REPORT -> Icons.Outlined.Edit
    "DECISION" -> Icons.Outlined.ThumbUp
    "PATROL_PLAN" -> Icons.Outlined.DateRange
    "OPERATION" -> Icons.Outlined.Build
    else -> Icons.Outlined.Info
}

private fun kindShortLabel(kind: String): String = when (kind) {
    "WARNING" -> "peringatan"
    KIND_CITIZEN_REPORT -> "laporan"
    "DECISION" -> "keputusan"
    "PATROL_PLAN" -> "rencana"
    "PREDICTION" -> "prediksi"
    "OPERATION" -> "operasi"
    else -> kind.lowercase()
}

/** Antrean mana yang punya halaman rincian di ponsel; selebihnya hanya di web. */
private fun kindDetailTab(kind: String): Tab? = when (kind) {
    "WARNING" -> Tab.PERINGATAN
    KIND_CITIZEN_REPORT -> Tab.LAPORAN
    "DECISION" -> Tab.REKOMENDASI
    else -> null
}

/** "2026-01-03T18:00:00+07:00" → "2026-01-03 18:00"; tanpa pustaka tanggal. */
private fun shortTime(iso: String): String = iso.take(16).replace('T', ' ')

// ---------------------------------------------------------------------------------
// Layar
// ---------------------------------------------------------------------------------

@Composable
fun PetugasScreen(state: PetugasState, actions: PetugasActions) {
    if (state.profile == null) {
        ScreenScaffold(busy = state.busy) {
            BrandHeader(stringResource(R.string.app_name), stringResource(R.string.subtitle), compact = true)
            LoginForm(state, actions)
            Version(state)
        }
        return
    }

    Scaffold(
        containerColor = PresisiColors.Base950,
        bottomBar = {
            if (state.detail == null) BottomMenu(state, actions)
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            Column(
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Column(Modifier.widthIn(max = 560.dp).fillMaxWidth()) {
                    val detail = state.detail
                    when {
                        detail != null -> DetailPage(detail, state, actions)
                        state.tab == Tab.ANTREAN -> QueueBoard(state, actions)
                        state.tab == Tab.PERINGATAN -> WarningList(state, actions)
                        state.tab == Tab.LAPORAN -> ReportList(state, actions)
                        state.tab == Tab.REKOMENDASI -> RecommendationList(state, actions)
                        state.tab == Tab.AKUN -> AccountPage(state, actions)
                    }
                }
            }
            if (state.busy) {
                CircularProgressIndicator(
                    color = PresisiColors.Accent,
                    modifier = Modifier.align(Alignment.TopCenter).padding(top = 8.dp),
                )
            }
        }
    }
}

@Composable
private fun BottomMenu(state: PetugasState, actions: PetugasActions) {
    NavigationBar(containerColor = PresisiColors.Base900, tonalElevation = 0.dp) {
        for (tab in state.tabs) {
            NavigationBarItem(
                selected = state.tab == tab,
                onClick = { actions.onTab(tab) },
                icon = { Icon(tab.icon, contentDescription = null) },
                label = { Text(stringResource(tab.label), fontSize = 11.sp) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = PresisiColors.Base950,
                    selectedTextColor = PresisiColors.Accent,
                    indicatorColor = PresisiColors.Accent,
                    unselectedIconColor = PresisiColors.InkMuted,
                    unselectedTextColor = PresisiColors.InkMuted,
                ),
            )
        }
    }
}

@Composable
private fun Version(state: PetugasState) {
    Text(
        "${stringResource(R.string.version_label)} ${state.version}",
        style = MaterialTheme.typography.bodySmall,
        modifier = Modifier.padding(top = 24.dp).fillMaxWidth(),
        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
    )
}

@Composable
private fun LoginForm(state: PetugasState, actions: PetugasActions) {
    Column(Modifier.padding(top = 18.dp)) {
        InputField(
            label = stringResource(R.string.username),
            value = state.username,
            onValueChange = actions.onUsername,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
        )
        InputField(
            label = stringResource(R.string.password),
            value = state.password,
            onValueChange = actions.onPassword,
            password = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
        )
        ErrorBox(state.loginError, Modifier.padding(top = 12.dp))
        PrimaryButton(
            text = stringResource(if (state.signingIn) R.string.signing_in else R.string.sign_in),
            onClick = actions.onSignIn,
            enabled = !state.signingIn,
            icon = Icons.Outlined.Lock,
            modifier = Modifier.padding(top = 16.dp),
        )
        Hint(stringResource(R.string.login_note), Modifier.padding(top = 12.dp))
    }
}

/** Judul tab dengan ikon, dipakai setiap halaman. */
@Composable
private fun PageTitle(text: String, icon: ImageVector, trailing: @Composable () -> Unit = {}) {
    Row(Modifier.fillMaxWidth().padding(bottom = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(10.dp))
        Text(text, style = MaterialTheme.typography.titleMedium, fontSize = 18.sp, modifier = Modifier.weight(1f))
        trailing()
    }
}

// ---------------------------------------------------------------------------------
// Antrean
// ---------------------------------------------------------------------------------

@Composable
private fun QueueBoard(state: PetugasState, actions: PetugasActions) {
    val profile = state.profile ?: return
    val feed = state.feed
    val look = roleLook(profile.role)

    BrandHeader(stringResource(R.string.app_name), stringResource(R.string.subtitle), compact = true)
    Column(Modifier.padding(top = 16.dp)) {
        Panel {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(look.icon, contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(30.dp))
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(profile.name, style = MaterialTheme.typography.titleMedium, fontSize = 15.sp)
                    Text(
                        profile.role.uppercase(),
                        fontSize = 10.sp,
                        letterSpacing = 1.2.sp,
                        color = PresisiColors.Accent,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
                if (feed != null) CountPill(feed.total)
            }
            Text(
                stringResource(look.tagline),
                style = MaterialTheme.typography.bodySmall,
                color = PresisiColors.InkMuted,
                modifier = Modifier.padding(top = 10.dp),
            )
        }

        if (feed != null) {
            if (feed.queues.isNotEmpty()) {
                SectionLabel(stringResource(R.string.queue_summary), Modifier.padding(top = 18.dp))
                Row(
                    Modifier.fillMaxWidth().padding(top = 8.dp).horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    for (queue in feed.queues) {
                        StatChip(kindIcon(queue.kind), queue.total, kindShortLabel(queue.kind))
                    }
                }
            }

            SectionLabel(stringResource(R.string.queue_title), Modifier.padding(top = 18.dp))
            when {
                feed.queues.isEmpty() -> Panel(Modifier.padding(top = 8.dp)) {
                    Text(stringResource(R.string.queue_empty), style = MaterialTheme.typography.bodyMedium, fontSize = 13.sp)
                }
                feed.total == 0 -> Panel(Modifier.padding(top = 8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = PresisiColors.Ok, modifier = Modifier.size(22.dp))
                        Spacer(Modifier.width(10.dp))
                        Text(stringResource(R.string.queue_all_clear), style = MaterialTheme.typography.bodyMedium)
                    }
                }
                else -> for (queue in feed.queues) {
                    if (queue.total == 0) continue
                    QueueCard(queue, actions, Modifier.padding(top = 8.dp))
                }
            }
        }

        Hint(state.note ?: stringResource(R.string.queue_note), Modifier.padding(top = 10.dp))
        Spacer(Modifier.height(12.dp))
        SecondaryButton(stringResource(R.string.refresh), onClick = actions.onRefresh, fullWidth = false, icon = Icons.Outlined.Refresh)
    }
}

/** Satu antrean. Baris yang punya halaman rincian dapat diketuk. */
@Composable
private fun QueueCard(queue: Api.Queue, actions: PetugasActions, modifier: Modifier = Modifier) {
    val target = kindDetailTab(queue.kind)
    Panel(modifier) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(kindIcon(queue.kind), contentDescription = null, tint = PresisiColors.Accent, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(queue.title, style = MaterialTheme.typography.titleMedium, fontSize = 14.sp)
                Text(queue.action, style = MaterialTheme.typography.bodySmall, color = PresisiColors.InkMuted)
            }
            CountPill(queue.total, Modifier.padding(start = 8.dp))
        }
        if (queue.items.isNotEmpty()) {
            Column(Modifier.padding(top = 10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                for (item in queue.items) {
                    val row = Modifier
                        .fillMaxWidth()
                        .let { if (target != null) it.clickable { actions.onOpen(DetailRef(target, item.code)) } else it }
                        .padding(vertical = 4.dp)
                    Row(row, verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(item.headline, style = MaterialTheme.typography.bodyLarge, fontSize = 13.sp)
                            if (item.detail.isNotBlank()) Text(item.detail, style = MaterialTheme.typography.bodySmall)
                        }
                        if (target != null) {
                            Icon(
                                Icons.AutoMirrored.Outlined.List,
                                contentDescription = null,
                                tint = PresisiColors.InkFaint,
                                modifier = Modifier.size(18.dp),
                            )
                        }
                    }
                }
            }
            if (target == null) Hint(stringResource(R.string.open_in_web), Modifier.padding(top = 6.dp))
        }
    }
}

// ---------------------------------------------------------------------------------
// Daftar
// ---------------------------------------------------------------------------------

@Composable
private fun <T> ListPage(
    title: String,
    icon: ImageVector,
    rows: List<T>?,
    basis: String,
    actions: PetugasActions,
    row: @Composable (T) -> Unit,
) {
    PageTitle(title, icon) {
        IconButton(onClick = actions.onRefresh) {
            Icon(Icons.Outlined.Refresh, contentDescription = stringResource(R.string.refresh), tint = PresisiColors.InkMuted)
        }
    }
    when {
        rows == null -> Hint(stringResource(R.string.list_loading))
        rows.isEmpty() -> Panel { Text(stringResource(R.string.list_empty), style = MaterialTheme.typography.bodyMedium) }
        else -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { for (item in rows) row(item) }
    }
    Hint(basis, Modifier.padding(top = 12.dp))
}

@Composable
private fun StatusTag(status: String) {
    val color = when (status) {
        "ACTIVE", "RECEIVED", "PENDING_REVIEW" -> PresisiColors.Critical
        "ACKNOWLEDGED", "VERIFIED", "FORWARDED", "IN_PROGRESS" -> PresisiColors.Warning
        else -> PresisiColors.InkFaint
    }
    Text(status, fontSize = 10.sp, fontWeight = FontWeight.Bold, color = color, letterSpacing = 1.sp)
}

@Composable
private fun ListRow(code: String, title: String, subtitle: String, status: String, onClick: () -> Unit) {
    Panel(Modifier.clickable(onClick = onClick)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(code, fontFamily = FontFamily.Monospace, fontSize = 11.sp, color = PresisiColors.InkMuted)
                Text(title, style = MaterialTheme.typography.bodyLarge, fontSize = 14.sp, modifier = Modifier.padding(top = 2.dp))
                Text(subtitle, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 2.dp))
            }
            Column(horizontalAlignment = Alignment.End) {
                StatusTag(status)
                Icon(Icons.AutoMirrored.Outlined.List, contentDescription = null, tint = PresisiColors.InkFaint, modifier = Modifier.size(18.dp).padding(top = 4.dp))
            }
        }
    }
}

@Composable
private fun WarningList(state: PetugasState, actions: PetugasActions) =
    ListPage(stringResource(R.string.tab_warnings), Icons.Outlined.Warning, state.warnings, stringResource(R.string.warning_basis), actions) { w ->
        ListRow(
            code = w.code,
            title = "${w.severity} · ${w.threatType}",
            subtitle = "${w.kelurahan.ifBlank { w.kecamatan }} · ${w.timeWindow} · skor ${w.riskScore}",
            status = w.status,
            onClick = { actions.onOpen(DetailRef(Tab.PERINGATAN, w.code)) },
        )
    }

@Composable
private fun ReportList(state: PetugasState, actions: PetugasActions) =
    ListPage(stringResource(R.string.tab_reports), Icons.Outlined.Edit, state.reports, stringResource(R.string.report_basis), actions) { r ->
        ListRow(
            code = r.code,
            title = r.category,
            subtitle = listOf(r.kelurahan.ifBlank { r.kecamatan }, shortTime(r.reportedAt)).filter { it.isNotBlank() }.joinToString(" · "),
            status = r.status,
            onClick = { actions.onOpen(DetailRef(Tab.LAPORAN, r.code)) },
        )
    }

@Composable
private fun RecommendationList(state: PetugasState, actions: PetugasActions) =
    ListPage(stringResource(R.string.tab_recommendations), Icons.Outlined.ThumbUp, state.recommendations, stringResource(R.string.recommendation_basis), actions) { r ->
        ListRow(
            code = r.code,
            title = "Untuk ${r.function} · prioritas ${r.priority}",
            subtitle = r.text.take(90),
            status = r.status,
            onClick = { actions.onOpen(DetailRef(Tab.REKOMENDASI, r.code)) },
        )
    }

// ---------------------------------------------------------------------------------
// Rincian
// ---------------------------------------------------------------------------------

@Composable
private fun DetailHeader(code: String, actions: PetugasActions) {
    Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = actions.onBack) {
            Icon(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = stringResource(R.string.back), tint = PresisiColors.Ink)
        }
        Text(code, fontFamily = FontFamily.Monospace, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = PresisiColors.Ink)
    }
}

@Composable
private fun Field(label: String, value: String) {
    if (value.isBlank()) return
    Column(Modifier.padding(top = 10.dp)) {
        Text(label.uppercase(), style = MaterialTheme.typography.labelSmall)
        Text(value, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 2.dp))
    }
}

@Composable
private fun DetailPage(detail: DetailRef, state: PetugasState, actions: PetugasActions) {
    DetailHeader(detail.code, actions)
    val acting = detail.code in state.acting
    when (detail.tab) {
        Tab.PERINGATAN -> {
            val w = state.warnings?.firstOrNull { it.code == detail.code }
            when {
                state.warnings == null -> Hint(stringResource(R.string.list_loading))
                w == null -> ErrorBox(stringResource(R.string.detail_not_found, detail.code))
                else -> Panel {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("${w.severity} · ${w.threatType}", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                        StatusTag(w.status)
                    }
                    Field(stringResource(R.string.label_region), listOf(w.kelurahan, w.kecamatan).filter { it.isNotBlank() }.joinToString(", "))
                    Field(stringResource(R.string.label_window), w.timeWindow)
                    Field(stringResource(R.string.label_score), "${w.riskScore} / 100")
                    Field(stringResource(R.string.label_confidence), "${w.confidence} / 100")
                    Field(stringResource(R.string.label_created), shortTime(w.createdAt))
                    Field("Prediksi", w.predictionCode)
                    Row(Modifier.padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        if (w.status == "ACTIVE" && state.allows(Perm.WARNING_ACK)) {
                            SecondaryButton(stringResource(R.string.acknowledge), onClick = { actions.onAcknowledge(w.code) }, enabled = !acting, fullWidth = false, icon = Icons.Outlined.Done)
                        }
                        if (w.status in setOf("ACTIVE", "ACKNOWLEDGED") && state.allows(Perm.WARNING_RESOLVE)) {
                            SecondaryButton(stringResource(R.string.resolve), onClick = { actions.onResolve(w.code) }, enabled = !acting, fullWidth = false, icon = Icons.Outlined.CheckCircle)
                        }
                    }
                }
            }
            Hint(stringResource(R.string.warning_basis), Modifier.padding(top = 12.dp))
        }
        Tab.LAPORAN -> {
            val r = state.reports?.firstOrNull { it.code == detail.code }
            when {
                state.reports == null -> Hint(stringResource(R.string.list_loading))
                r == null -> ErrorBox(stringResource(R.string.detail_not_found, detail.code))
                else -> Panel {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(r.category, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                        StatusTag(r.status)
                    }
                    Field("Keterangan", r.description)
                    Field(stringResource(R.string.label_region), listOf(r.kelurahan, r.kecamatan).filter { it.isNotBlank() }.joinToString(", "))
                    Field("Keterangan tempat", r.locationText)
                    Field(stringResource(R.string.label_reported), shortTime(r.reportedAt))
                    Field(stringResource(R.string.label_attach_count), if (r.attachments > 0) "${r.attachments} berkas (dibuka di web)" else "")
                    if (r.status == "RECEIVED" && state.allows(Perm.REPORT_WRITE)) {
                        SecondaryButton(
                            text = stringResource(if (acting) R.string.verifying else R.string.verify),
                            onClick = { actions.onVerify(r.code) },
                            enabled = !acting,
                            fullWidth = false,
                            icon = Icons.Outlined.Done,
                            modifier = Modifier.padding(top = 14.dp),
                        )
                    }
                }
            }
            Hint(stringResource(R.string.report_basis), Modifier.padding(top = 12.dp))
        }
        Tab.REKOMENDASI -> {
            val r = state.recommendations?.firstOrNull { it.code == detail.code }
            when {
                state.recommendations == null -> Hint(stringResource(R.string.list_loading))
                r == null -> ErrorBox(stringResource(R.string.detail_not_found, detail.code))
                else -> {
                    Panel {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Untuk ${r.function}", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                            StatusTag(r.status)
                        }
                        Field("Rekomendasi", r.text)
                        Field(stringResource(R.string.label_priority), r.priority)
                        Field(stringResource(R.string.label_created), shortTime(r.createdAt))
                        Field("Prediksi", r.predictionCode)
                        Field("Peringatan", r.warningCode)
                    }
                    if (r.status == "PENDING_REVIEW" && state.allows(Perm.DECIDE)) {
                        DecisionForm(r, state, actions, acting)
                    }
                }
            }
            Hint(stringResource(R.string.recommendation_basis), Modifier.padding(top = 12.dp))
        }
        else -> Hint(stringResource(R.string.open_in_web))
    }
}

/** Formulir keputusan Pimpinan. Aturan isi dijaga server; di sini hanya pengingat dini. */
@Composable
private fun DecisionForm(r: Api.Recommendation, state: PetugasState, actions: PetugasActions, acting: Boolean) {
    Panel(Modifier.padding(top = 10.dp), borderColor = PresisiColors.Accent.copy(alpha = 0.5f)) {
        SectionLabel(stringResource(R.string.decision_title), icon = Icons.Outlined.Star)
        Row(Modifier.padding(top = 8.dp).horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            for ((value, label) in listOf("APPROVED" to R.string.decision_approve, "MODIFIED" to R.string.decision_modify, "REJECTED" to R.string.decision_reject)) {
                FilterChip(
                    selected = state.decisionChoice == value,
                    onClick = { actions.onDecisionChoice(value) },
                    label = { Text(stringResource(label), fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = PresisiColors.Accent,
                        selectedLabelColor = PresisiColors.Base950,
                        labelColor = PresisiColors.Ink,
                    ),
                )
            }
        }
        if (state.decisionChoice == "MODIFIED") {
            InputField(stringResource(R.string.decision_text), state.decisionText, actions.onDecisionText, minLines = 3, maxLength = 4000)
        }
        InputField(stringResource(R.string.decision_reason), state.decisionReason, actions.onDecisionReason, minLines = 2, maxLength = 2000)
        PrimaryButton(
            text = stringResource(if (acting) R.string.decision_submitting else R.string.decision_submit),
            onClick = { actions.onDecide(r.code) },
            enabled = !acting,
            icon = Icons.Outlined.Done,
            modifier = Modifier.padding(top = 12.dp),
        )
    }
}

// ---------------------------------------------------------------------------------
// Akun
// ---------------------------------------------------------------------------------

@Composable
private fun AccountPage(state: PetugasState, actions: PetugasActions) {
    val profile = state.profile ?: return
    PageTitle(stringResource(R.string.account_title), Icons.Outlined.AccountCircle)
    Panel {
        Text(profile.name, style = MaterialTheme.typography.titleMedium)
        Text(profile.role, style = MaterialTheme.typography.bodyMedium, color = PresisiColors.Accent)
        Text(stringResource(roleLook(profile.role).tagline), style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 6.dp))
    }
    SectionLabel(stringResource(R.string.account_permissions), Modifier.padding(top = 16.dp))
    Panel(Modifier.padding(top = 8.dp)) {
        if (profile.permissions.isEmpty()) {
            Text("—", style = MaterialTheme.typography.bodyMedium)
        } else {
            for (permission in profile.permissions.sorted()) {
                Text(permission, fontFamily = FontFamily.Monospace, fontSize = 12.sp, color = PresisiColors.InkMuted)
            }
        }
    }
    Spacer(Modifier.height(16.dp))
    SecondaryButton(stringResource(R.string.sign_out), onClick = actions.onSignOut, fullWidth = false, icon = Icons.AutoMirrored.Outlined.ExitToApp)
    Version(state)
}

// ---------------------------------------------------------------------------------
// Pratinjau
// ---------------------------------------------------------------------------------

private val NO_ACTIONS = PetugasActions({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})

private val PREVIEW_PROFILE = Api.Profile(
    "Bripka Contoh", "Polsek",
    listOf(Perm.WARNING_READ, Perm.WARNING_ACK, Perm.REPORT_READ, Perm.REPORT_WRITE),
)

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 640)
@Composable
private fun LoginPreview() {
    PresisiTheme { PetugasScreen(PetugasState(loginError = "Sesi Anda berakhir.", version = "2.4.0"), NO_ACTIONS) }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 900)
@Composable
private fun QueuePreview() {
    PresisiTheme {
        PetugasScreen(
            PetugasState(
                profile = PREVIEW_PROFILE,
                feed = Api.Feed(
                    role = "Polsek", total = 3,
                    queues = listOf(
                        Api.Queue("WARNING", "Peringatan belum diterima", "Terima atau selesaikan", 2, listOf(Api.QueueItem("WRN-00012", "HIGH — CURANMOR", "Tebet · skor 78"))),
                        Api.Queue(KIND_CITIZEN_REPORT, "Laporan warga menunggu triase", "Verifikasi", 1, listOf(Api.QueueItem("CR-2026-0042", "Pencurian", "Motor hilang di depan rumah."))),
                    ),
                ),
                version = "2.4.0",
            ),
            NO_ACTIONS,
        )
    }
}

@Preview(showBackground = true, backgroundColor = 0xFF050B18, widthDp = 360, heightDp = 800)
@Composable
private fun WarningDetailPreview() {
    PresisiTheme {
        PetugasScreen(
            PetugasState(
                profile = PREVIEW_PROFILE,
                tab = Tab.PERINGATAN,
                detail = DetailRef(Tab.PERINGATAN, "WRN-00012"),
                warnings = listOf(Api.Warning("WRN-00012", "HIGH", "CURANMOR", "18:00-23:59", 78, 40, "ACTIVE", "Tebet", "Tebet Timur", "2026-01-03T06:00:00+07:00", "PRD-00981")),
                version = "2.4.0",
            ),
            NO_ACTIONS,
        )
    }
}
