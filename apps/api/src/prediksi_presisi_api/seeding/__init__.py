"""Pemuatan data dummy ke database (PHASE 3).

Prinsip:

1. `data/sample/` tetap sumber data dummy kanonik; pemuatan tidak menyunting berkasnya.
2. Pemetaan nilai Bahasa Indonesia → enum tersimpan berasal dari `config/taxonomy/`,
   bukan dari kode (docs/02 §22).
3. **Fail-fast**: baris yang melanggar integritas menghentikan seed, tidak dikoreksi
   diam-diam (CLAUDE.md §17, docs/08 PHASE 3 acceptance A-1).
4. Idempoten: menjalankan ulang seed tidak menggandakan baris.
"""

from .errors import SeedError
from .taxonomy import Taxonomy, load_taxonomy

__all__ = ["SeedError", "Taxonomy", "load_taxonomy"]
