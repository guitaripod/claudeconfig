"""Synthetic app text for the T03-xcstrings-bulk eval: one table per catalog key, one line per locale.

Simple keys are "locale value" lines. Plural keys are "locale category=value|category=value" lines.
"""

LOCALES = [
    "ar", "bg", "ca", "cs", "da", "de", "el", "en-AU", "en-CA", "en-GB", "es", "es-MX", "fi", "fr", "fr-CA",
    "he", "hi", "hr", "hu", "id", "it", "ja", "ko", "ms", "nb", "nl", "pl", "pt-BR", "pt-PT", "ro", "ru", "sk",
    "sv", "th", "tr", "uk", "vi", "zh-Hans", "zh-Hant",
]

LOCALIZABLE_EXISTING = {
    "album.new": """
en New Album
ar ألبوم جديد
bg Нов албум
ca Àlbum nou
cs Nové album
da Nyt album
de Neues Album
el Νέο άλμπουμ
en-AU New Album
en-CA New Album
en-GB New Album
es Nuevo álbum
es-MX Nuevo álbum
fi Uusi albumi
fr Nouvel album
fr-CA Nouvel album
he אלבום חדש
hi नया एल्बम
hr Novi album
hu Új album
id Album baru
it Nuovo album
ja 新規アルバム
ko 새 앨범
ms Album baharu
nb Nytt album
nl Nieuw album
pl Nowy album
pt-BR Novo álbum
pt-PT Novo álbum
ro Album nou
ru Новый альбом
sk Nový album
sv Nytt album
th อัลบั้มใหม่
tr Yeni albüm
uk Новий альбом
vi Album mới
zh-Hans 新建相册
zh-Hant 新增相簿
""",
    "common.cancel": """
en Cancel
ar إلغاء
bg Отказ
ca Cancel·la
cs Zrušit
da Annuller
de Abbrechen
el Ακύρωση
en-AU Cancel
en-CA Cancel
en-GB Cancel
es Cancelar
es-MX Cancelar
fi Peruuta
fr Annuler
fr-CA Annuler
he ביטול
hi रद्द करें
hr Odustani
hu Mégse
id Batal
it Annulla
ja キャンセル
ko 취소
ms Batal
nb Avbryt
nl Annuleren
pl Anuluj
pt-BR Cancelar
pt-PT Cancelar
ro Anulează
ru Отмена
sk Zrušiť
sv Avbryt
th ยกเลิก
tr İptal
uk Скасувати
vi Hủy
zh-Hans 取消
zh-Hant 取消
""",
    "common.delete": """
en Delete
ar حذف
bg Изтриване
ca Suprimeix
cs Smazat
da Slet
de Löschen
el Διαγραφή
en-AU Delete
en-CA Delete
en-GB Delete
es Eliminar
es-MX Eliminar
fi Poista
fr Supprimer
fr-CA Supprimer
he מחיקה
hi हटाएं
hr Izbriši
hu Törlés
id Hapus
it Elimina
ja 削除
ko 삭제
ms Padam
nb Slett
nl Verwijderen
pl Usuń
pt-BR Excluir
pt-PT Eliminar
ro Șterge
ru Удалить
sk Vymazať
sv Radera
th ลบ
tr Sil
uk Видалити
vi Xóa
zh-Hans 删除
zh-Hant 刪除
""",
    "common.done": """
en Done
ar تم
bg Готово
ca Fet
cs Hotovo
da Udført
de Fertig
el Τέλος
en-AU Done
en-CA Done
en-GB Done
es Listo
es-MX Listo
fi Valmis
fr OK
fr-CA OK
he סיום
hi हो गया
hr Gotovo
hu Kész
id Selesai
it Fine
ja 完了
ko 완료
ms Selesai
nb Ferdig
nl Gereed
pl Gotowe
pt-BR Concluído
pt-PT Concluído
ro Gata
ru Готово
sk Hotovo
sv Klar
th เสร็จแล้ว
tr Bitti
uk Готово
vi Xong
zh-Hans 完成
zh-Hant 完成
""",
    "common.retry": """
en Try Again
ar حاول مرة أخرى
bg Опитай отново
ca Torna-ho a provar
cs Zkusit znovu
da Prøv igen
de Erneut versuchen
el Δοκίμασε ξανά
en-AU Try Again
en-CA Try Again
en-GB Try Again
es Reintentar
es-MX Reintentar
fi Yritä uudelleen
fr Réessayer
fr-CA Réessayer
he נסה שוב
hi फिर से कोशिश करें
hr Pokušaj ponovo
hu Próbáld újra
id Coba lagi
it Riprova
ja 再試行
ko 다시 시도
ms Cuba lagi
nb Prøv igjen
nl Opnieuw proberen
pl Spróbuj ponownie
pt-BR Tentar novamente
pt-PT Tentar novamente
ro Încearcă din nou
ru Повторить
sk Skúsiť znova
sv Försök igen
th ลองอีกครั้ง
tr Yeniden dene
uk Спробувати знову
vi Thử lại
zh-Hans 重试
zh-Hant 重試
""",
    "common.save": """
en Save
ar حفظ
bg Запази
ca Desa
cs Uložit
da Gem
de Speichern
el Αποθήκευση
en-AU Save
en-CA Save
en-GB Save
es Guardar
es-MX Guardar
fi Tallenna
fr Enregistrer
fr-CA Enregistrer
he שמור
hi सहेजें
hr Spremi
hu Mentés
id Simpan
it Salva
ja 保存
ko 저장
ms Simpan
nb Lagre
nl Bewaren
pl Zapisz
pt-BR Salvar
pt-PT Guardar
ro Salvează
ru Сохранить
sk Uložiť
sv Spara
th บันทึก
tr Kaydet
uk Зберегти
vi Lưu
zh-Hans 保存
zh-Hant 儲存
""",
    "journal.empty": """
en No entries yet
ar لا توجد إدخالات بعد
bg Все още няма записи
ca Encara no hi ha entrades
cs Zatím žádné záznamy
da Ingen indlæg endnu
de Noch keine Einträge
el Δεν υπάρχουν καταχωρίσεις ακόμα
en-AU No entries yet
en-CA No entries yet
en-GB No entries yet
es Todavía no hay entradas
es-MX Todavía no hay entradas
fi Ei merkintöjä vielä
fr Aucune entrée pour l’instant
fr-CA Aucune entrée pour l’instant
he אין עדיין רשומות
hi अभी कोई प्रविष्टि नहीं है
hr Još nema unosa
hu Még nincs bejegyzés
id Belum ada entri
it Nessuna voce per ora
ja まだエントリーがありません
ko 아직 항목이 없습니다
ms Belum ada catatan
nb Ingen oppføringer ennå
nl Nog geen items
pl Brak wpisów
pt-BR Nenhuma entrada ainda
pt-PT Ainda não há entradas
ro Nicio intrare încă
ru Записей пока нет
sk Zatiaľ žiadne záznamy
sv Inga inlägg än
th ยังไม่มีรายการ
tr Henüz kayıt yok
uk Записів поки немає
vi Chưa có mục nào
zh-Hans 还没有任何条目
zh-Hant 還沒有任何項目
""",
    "photo.favorite": """
en Favorite
ar مفضلة
bg Любими
ca Preferit
cs Oblíbené
da Favorit
de Favorit
el Αγαπημένο
en-AU Favourite
en-CA Favourite
en-GB Favourite
es Favorito
es-MX Favorito
fi Suosikki
fr Favori
fr-CA Favori
he מועדף
hi पसंदीदा
hr Favorit
hu Kedvenc
id Favorit
it Preferito
ja お気に入り
ko 즐겨찾기
ms Kegemaran
nb Favoritt
nl Favoriet
pl Ulubione
pt-BR Favorito
pt-PT Favorito
ro Preferat
ru Избранное
sk Obľúbené
sv Favorit
th รายการโปรด
tr Favori
uk Вибране
vi Yêu thích
zh-Hans 收藏
zh-Hant 最愛
""",
    "photo.share": """
en Share
ar مشاركة
bg Споделяне
ca Comparteix
cs Sdílet
da Del
de Teilen
el Κοινοποίηση
en-AU Share
en-CA Share
en-GB Share
es Compartir
es-MX Compartir
fi Jaa
fr Partager
fr-CA Partager
he שתף
hi शेयर करें
hr Dijeli
hu Megosztás
id Bagikan
it Condividi
ja 共有
ko 공유
ms Kongsi
nb Del
nl Delen
pl Udostępnij
pt-BR Compartilhar
pt-PT Partilhar
ro Partajează
ru Поделиться
sk Zdieľať
sv Dela
th แชร์
tr Paylaş
uk Поділитися
vi Chia sẻ
zh-Hans 分享
zh-Hant 分享
""",
    "settings.title": """
en Settings
ar الإعدادات
bg Настройки
ca Configuració
cs Nastavení
da Indstillinger
de Einstellungen
el Ρυθμίσεις
en-AU Settings
en-CA Settings
en-GB Settings
es Ajustes
es-MX Configuración
fi Asetukset
fr Réglages
fr-CA Réglages
he הגדרות
hi सेटिंग्स
hr Postavke
hu Beállítások
id Pengaturan
it Impostazioni
ja 設定
ko 설정
ms Tetapan
nb Innstillinger
nl Instellingen
pl Ustawienia
pt-BR Ajustes
pt-PT Definições
ro Setări
ru Настройки
sk Nastavenia
sv Inställningar
th การตั้งค่า
tr Ayarlar
uk Налаштування
vi Cài đặt
zh-Hans 设置
zh-Hant 設定
""",
    "tab.albums": """
en Albums
ar الألبومات
bg Албуми
ca Àlbums
cs Alba
da Albummer
de Alben
el Άλμπουμ
en-AU Albums
en-CA Albums
en-GB Albums
es Álbumes
es-MX Álbumes
fi Albumit
fr Albums
fr-CA Albums
he אלבומים
hi एल्बम
hr Albumi
hu Albumok
id Album
it Album
ja アルバム
ko 앨범
ms Album
nb Album
nl Albums
pl Albumy
pt-BR Álbuns
pt-PT Álbuns
ro Albume
ru Альбомы
sk Albumy
sv Album
th อัลบั้ม
tr Albümler
uk Альбоми
vi Album
zh-Hans 相册
zh-Hant 相簿
""",
    "tab.journal": """
en Journal
ar اليوميات
bg Дневник
ca Diari
cs Deník
da Dagbog
de Tagebuch
el Ημερολόγιο
en-AU Journal
en-CA Journal
en-GB Journal
es Diario
es-MX Diario
fi Päiväkirja
fr Journal
fr-CA Journal
he יומן
hi जर्नल
hr Dnevnik
hu Napló
id Jurnal
it Diario
ja ジャーナル
ko 저널
ms Jurnal
nb Dagbok
nl Dagboek
pl Dziennik
pt-BR Diário
pt-PT Diário
ro Jurnal
ru Дневник
sk Denník
sv Dagbok
th เจอร์นัล
tr Günlük
uk Журнал
vi Nhật ký
zh-Hans 日记
zh-Hant 日誌
""",
}

LOCALIZABLE_NEW = {
    "album.delete.confirm": """
en Delete “%@”? This can’t be undone.
ar هل تريد حذف “%@”؟ لا يمكن التراجع عن هذا.
bg Да се изтрие ли „%@“? Това действие не може да бъде отменено.
ca Vols suprimir «%@»? Aquesta acció no es pot desfer.
cs Smazat „%@“? Tuto akci nelze vrátit zpět.
da Slet „%@“? Dette kan ikke fortrydes.
de „%@“ löschen? Das kann nicht rückgängig gemacht werden.
el Διαγραφή του «%@»; Αυτό δεν μπορεί να αναιρεθεί.
en-AU Delete “%@”? This can’t be undone.
en-CA Delete “%@”? This can’t be undone.
en-GB Delete “%@”? This can’t be undone.
es ¿Eliminar «%@»? Esta acción no se puede deshacer.
es-MX ¿Eliminar «%@»? Esta acción no se puede deshacer.
fi Poistetaanko ”%@”? Tätä ei voi perua.
fr Supprimer « %@ » ? Cette action est irréversible.
fr-CA Supprimer « %@ » ? Cette action est irréversible.
he למחוק את „%@“? לא ניתן לבטל פעולה זו.
hi “%@” हटाएं? इसे पूर्ववत नहीं किया जा सकता।
hr Izbrisati „%@“? Ovo se ne može poništiti.
hu Törli a(z) „%@” albumot? Ez a művelet nem vonható vissza.
id Hapus “%@”? Tindakan ini tidak dapat dibatalkan.
it Eliminare «%@»? Questa operazione non può essere annullata.
ja 「%@」を削除しますか？この操作は取り消せません。
ko “%@”을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
ms Padam “%@”? Tindakan ini tidak boleh dibatalkan.
nb Slette «%@»? Dette kan ikke angres.
nl “%@” verwijderen? Dit kan niet ongedaan worden gemaakt.
pl Usunąć „%@”? Tej operacji nie można cofnąć.
pt-BR Excluir “%@”? Isso não pode ser desfeito.
pt-PT Eliminar “%@”? Isto não pode ser anulado.
ro Ștergi „%@”? Această acțiune nu poate fi anulată.
ru Удалить «%@»? Это действие нельзя отменить.
sk Vymazať „%@“? Túto akciu nie je možné vrátiť späť.
sv Radera ”%@”? Detta kan inte ångras.
th ลบ “%@” ใช่หรือไม่? การดำเนินการนี้ไม่สามารถยกเลิกได้
tr “%@” silinsin mi? Bu işlem geri alınamaz.
uk Видалити «%@»? Цю дію не можна скасувати.
vi Xóa “%@”? Thao tác này không thể hoàn tác.
zh-Hans 删除“%@”？此操作无法撤销。
zh-Hant 刪除「%@」？此操作無法復原。
""",
    "welcome.back": """
en Welcome back, %@!
ar مرحبًا بعودتك، %@!
bg Добре дошъл отново, %@!
ca Benvingut de nou, %@!
cs Vítej zpět, %@!
da Velkommen tilbage, %@!
de Willkommen zurück, %@!
el Καλώς ήρθες ξανά, %@!
en-AU Welcome back, %@!
en-CA Welcome back, %@!
en-GB Welcome back, %@!
es ¡Bienvenido de nuevo, %@!
es-MX ¡Qué bueno verte de nuevo, %@!
fi Tervetuloa takaisin, %@!
fr Bon retour, %@ !
fr-CA Bon retour, %@ !
he ברוך שובך, %@!
hi वापसी पर स्वागत है, %@!
hr Dobro došao natrag, %@!
hu Üdv újra itthon, %@!
id Selamat datang kembali, %@!
it Bentornato, %@!
ja おかえりなさい、%@さん！
ko 다시 오신 것을 환영합니다, %@님!
ms Selamat kembali, %@!
nb Velkommen tilbake, %@!
nl Welkom terug, %@!
pl Witaj ponownie, %@!
pt-BR Bem-vindo de volta, %@!
pt-PT Bem-vindo de volta, %@!
ro Bine ai revenit, %@!
ru С возвращением, %@!
sk Vitaj späť, %@!
sv Välkommen tillbaka, %@!
th ยินดีต้อนรับกลับ %@!
tr Tekrar hoş geldin, %@!
uk З поверненням, %@!
vi Chào mừng bạn trở lại, %@!
zh-Hans 欢迎回来，%@！
zh-Hant 歡迎回來，%@！
""",
    "sync.paused.lowpower": """
en Sync is paused while Low Power Mode is on.
ar تم إيقاف المزامنة مؤقتًا أثناء تشغيل وضع الطاقة المنخفضة.
bg Синхронизирането е на пауза, докато е включен режимът за ниско захранване.
ca La sincronització està en pausa mentre el mode d’energia baixa estigui activat.
cs Synchronizace je pozastavena, dokud je zapnutý režim nízké spotřeby.
da Synkronisering er sat på pause, mens lavenergitilstand er aktiveret.
de Die Synchronisierung ist pausiert, solange der Stromsparmodus aktiviert ist.
el Ο συγχρονισμός είναι σε παύση όσο είναι ενεργή η Λειτουργία χαμηλής ισχύος.
en-AU Sync is paused while Low Power Mode is on.
en-CA Sync is paused while Low Power Mode is on.
en-GB Sync is paused while Low Power Mode is on.
es La sincronización está en pausa mientras el modo de bajo consumo esté activado.
es-MX La sincronización está en pausa mientras el modo de bajo consumo esté activado.
fi Synkronointi on keskeytetty, kun virransäästötila on päällä.
fr La synchronisation est suspendue tant que le mode Économie d’énergie est activé.
fr-CA La synchronisation est suspendue tant que le mode Économie d’énergie est activé.
he הסנכרון מושהה כל עוד מצב חיסכון בסוללה פעיל.
hi कम पावर मोड चालू होने पर सिंक रोक दिया जाता है।
hr Sinkronizacija je pauzirana dok je uključen način rada za nisku potrošnju.
hu A szinkronizálás szünetel, amíg az energiatakarékos mód be van kapcsolva.
id Sinkronisasi dijeda saat Mode Daya Rendah aktif.
it La sincronizzazione è in pausa finché la Modalità a basso consumo è attiva.
ja 低電力モードがオンの間、同期は一時停止されます。
ko 저전력 모드가 켜져 있는 동안에는 동기화가 일시 중지됩니다.
ms Penyegerakan dijeda semasa Mod Kuasa Rendah dihidupkan.
nb Synkronisering er satt på pause mens strømsparingsmodus er på.
nl Synchronisatie is gepauzeerd zolang de energiebesparingsstand aan staat.
pl Synchronizacja jest wstrzymana, gdy włączony jest tryb niskiego zużycia energii.
pt-BR A sincronização fica pausada enquanto o Modo de Economia de Energia estiver ativado.
pt-PT A sincronização está em pausa enquanto o Modo de Poupança de Energia estiver ativo.
ro Sincronizarea este pusă pe pauză cât timp modul Economie de energie este activat.
ru Синхронизация приостановлена, пока включен режим энергосбережения.
sk Synchronizácia je pozastavená, kým je zapnutý režim nízkej spotreby.
sv Synkroniseringen är pausad medan energisparläget är på.
th การซิงค์หยุดชั่วคราวขณะเปิดโหมดประหยัดพลังงาน
tr Düşük Güç Modu açıkken eşitleme duraklatılır.
uk Синхронізацію призупинено, поки ввімкнено режим енергозбереження.
vi Đồng bộ bị tạm dừng khi Chế độ Tiết kiệm Pin đang bật.
zh-Hans 开启低电量模式时，同步已暂停。
zh-Hant 開啟低電量模式時，同步已暫停。
""",
    "storage.used": """
en %1$@ of %2$@ used
ar تم استخدام %1$@ من أصل %2$@
bg Използвани: %1$@ от %2$@
ca %1$@ de %2$@ utilitzats
cs Použito %1$@ z %2$@
da %1$@ af %2$@ brugt
de %1$@ von %2$@ belegt
el Χρησιμοποιούνται %1$@ από %2$@
en-AU %1$@ of %2$@ used
en-CA %1$@ of %2$@ used
en-GB %1$@ of %2$@ used
es %1$@ de %2$@ usados
es-MX %1$@ de %2$@ usados
fi %1$@ / %2$@ käytetty
fr %1$@ sur %2$@ utilisés
fr-CA %1$@ sur %2$@ utilisés
he נוצלו %1$@ מתוך %2$@
hi %2$@ में से %1$@ उपयोग किए गए
hr Upotrijebljeno %1$@ od %2$@
hu %1$@ / %2$@ használva
id %1$@ dari %2$@ digunakan
it %1$@ su %2$@ utilizzati
ja %2$@ 中 %1$@ を使用
ko %2$@ 중 %1$@ 사용됨
ms %1$@ daripada %2$@ digunakan
nb %1$@ av %2$@ brukt
nl %1$@ van %2$@ gebruikt
pl Wykorzystano %1$@ z %2$@
pt-BR %1$@ de %2$@ usados
pt-PT %1$@ de %2$@ utilizados
ro %1$@ din %2$@ utilizați
ru Использовано %1$@ из %2$@
sk Použité %1$@ z %2$@
sv %1$@ av %2$@ använt
th ใช้ไปแล้ว %1$@ จาก %2$@
tr %2$@ içinden %1$@ kullanıldı
uk Використано %1$@ з %2$@
vi Đã dùng %1$@ trên %2$@
zh-Hans 已使用 %1$@，共 %2$@
zh-Hant 已使用 %1$@，共 %2$@
""",
    "album.move.summary": """
en Move %2$lld photos from “%1$@”
ar نقل %2$lld صورة من “%1$@”
bg Преместване на %2$lld снимки от „%1$@“
ca Mou %2$lld fotos des de «%1$@»
cs Přesunout %2$lld fotek z „%1$@“
da Flyt %2$lld fotoer fra „%1$@“
de %2$lld Fotos aus „%1$@“ verschieben
el Μετακίνηση %2$lld φωτογραφιών από το «%1$@»
en-AU Move %2$lld photos from “%1$@”
en-CA Move %2$lld photos from “%1$@”
en-GB Move %2$lld photos from “%1$@”
es Mover %2$lld fotos de «%1$@»
es-MX Mover %2$lld fotos de «%1$@»
fi Siirrä %2$lld kuvaa albumista ”%1$@”
fr Déplacer %2$lld photos depuis « %1$@ »
fr-CA Déplacer %2$lld photos depuis « %1$@ »
he העברת %2$lld תמונות מ-„%1$@“
hi “%1$@” से %2$lld फ़ोटो ले जाएँ
hr Premjesti %2$lld fotografija iz „%1$@“
hu %2$lld fotó áthelyezése innen: „%1$@”
id Pindahkan %2$lld foto dari “%1$@”
it Sposta %2$lld foto da «%1$@»
ja 「%1$@」から %2$lld 枚の写真を移動
ko “%1$@”에서 사진 %2$lld장 이동
ms Alihkan %2$lld foto daripada “%1$@”
nb Flytt %2$lld bilder fra «%1$@»
nl %2$lld foto’s verplaatsen uit “%1$@”
pl Przenieś %2$lld zdjęć z „%1$@”
pt-BR Mover %2$lld fotos de “%1$@”
pt-PT Mover %2$lld fotografias de “%1$@”
ro Mută %2$lld fotografii din „%1$@”
ru Переместить %2$lld фотографий из «%1$@»
sk Presunúť %2$lld fotografií z „%1$@“
sv Flytta %2$lld foton från ”%1$@”
th ย้ายรูปภาพ %2$lld รูปจาก “%1$@”
tr “%1$@” içinden %2$lld fotoğrafı taşı
uk Перемістити %2$lld фотографій з «%1$@»
vi Chuyển %2$lld ảnh từ “%1$@”
zh-Hans 将 %2$lld 张照片从“%1$@”移动
zh-Hant 將 %2$lld 張照片從「%1$@」移動
""",
    "import.failed.reason": """
en Import failed: %@
ar فشل الاستيراد: %@
bg Неуспешен импорт: %@
ca No s’ha pogut importar: %@
cs Import se nezdařil: %@
da Import mislykkedes: %@
de Import fehlgeschlagen: %@
el Η εισαγωγή απέτυχε: %@
en-AU Import failed: %@
en-CA Import failed: %@
en-GB Import failed: %@
es Error al importar: %@
es-MX Error al importar: %@
fi Tuonti epäonnistui: %@
fr Échec de l’importation : %@
fr-CA Échec de l’importation : %@
he הייבוא נכשל: %@
hi आयात विफल रहा: %@
hr Uvoz nije uspio: %@
hu Az importálás sikertelen: %@
id Impor gagal: %@
it Importazione non riuscita: %@
ja インポートに失敗しました: %@
ko 가져오기 실패: %@
ms Import gagal: %@
nb Importen mislyktes: %@
nl Importeren mislukt: %@
pl Import nie powiódł się: %@
pt-BR Falha na importação: %@
pt-PT Falha na importação: %@
ro Importul a eșuat: %@
ru Не удалось импортировать: %@
sk Import zlyhal: %@
sv Importen misslyckades: %@
th นำเข้าไม่สำเร็จ: %@
tr İçe aktarma başarısız: %@
uk Не вдалося імпортувати: %@
vi Nhập thất bại: %@
zh-Hans 导入失败：%@
zh-Hant 匯入失敗：%@
""",
    "sync.last.updated": """
en Last synced %@
ar آخر مزامنة: %@
bg Последно синхронизиране: %@
ca Última sincronització: %@
cs Naposledy synchronizováno: %@
da Senest synkroniseret: %@
de Zuletzt synchronisiert: %@
el Τελευταίος συγχρονισμός: %@
en-AU Last synced %@
en-CA Last synced %@
en-GB Last synced %@
es Última sincronización: %@
es-MX Última sincronización: %@
fi Viimeksi synkronoitu: %@
fr Dernière synchronisation : %@
fr-CA Dernière synchronisation : %@
he סונכרן לאחרונה: %@
hi आखिरी बार सिंक: %@
hr Zadnja sinkronizacija: %@
hu Utolsó szinkronizálás: %@
id Terakhir disinkronkan %@
it Ultima sincronizzazione: %@
ja 最終同期: %@
ko 마지막 동기화: %@
ms Kali terakhir disegerakkan %@
nb Sist synkronisert: %@
nl Laatst gesynchroniseerd: %@
pl Ostatnio zsynchronizowano: %@
pt-BR Última sincronização: %@
pt-PT Última sincronização: %@
ro Ultima sincronizare: %@
ru Последняя синхронизация: %@
sk Naposledy synchronizované: %@
sv Senast synkroniserad: %@
th ซิงค์ล่าสุด: %@
tr Son eşitleme: %@
uk Остання синхронізація: %@
vi Đồng bộ lần cuối: %@
zh-Hans 上次同步：%@
zh-Hant 上次同步：%@
""",
    "share.link.copied": """
en Link copied
ar تم نسخ الرابط
bg Връзката е копирана
ca Enllaç copiat
cs Odkaz byl zkopírován
da Link kopieret
de Link kopiert
el Ο σύνδεσμος αντιγράφηκε
en-AU Link copied
en-CA Link copied
en-GB Link copied
es Enlace copiado
es-MX Enlace copiado
fi Linkki kopioitu
fr Lien copié
fr-CA Lien copié
he הקישור הועתק
hi लिंक कॉपी किया गया
hr Poveznica kopirana
hu Hivatkozás másolva
id Tautan disalin
it Link copiato
ja リンクをコピーしました
ko 링크가 복사됨
ms Pautan disalin
nb Lenke kopiert
nl Link gekopieerd
pl Link skopiowany
pt-BR Link copiado
pt-PT Ligação copiada
ro Link copiat
ru Ссылка скопирована
sk Odkaz bol skopírovaný
sv Länken kopierades
th คัดลอกลิงก์แล้ว
tr Bağlantı kopyalandı
uk Посилання скопійовано
vi Đã sao chép liên kết
zh-Hans 链接已复制
zh-Hant 連結已複製
""",
}

LOCALIZABLE_PLURAL = {
    "export.success": """
en one=Exported %lld photo|other=Exported %lld photos
ar zero=تم تصدير %lld من الصور|one=تم تصدير %lld صورة|two=تم تصدير %lld صورتين|few=تم تصدير %lld صور|many=تم تصدير %lld صورة|other=تم تصدير %lld صورة
bg one=Експортирана е %lld снимка|other=Експортирани са %lld снимки
ca one=S’ha exportat %lld foto|other=S’han exportat %lld fotos
cs one=Exportována %lld fotka|few=Exportovány %lld fotky|many=Exportováno %lld fotky|other=Exportováno %lld fotek
da one=Eksporterede %lld foto|other=Eksporterede %lld fotoer
de one=%lld Foto exportiert|other=%lld Fotos exportiert
el one=Εξήχθη %lld φωτογραφία|other=Εξήχθησαν %lld φωτογραφίες
en-AU one=Exported %lld photo|other=Exported %lld photos
en-CA one=Exported %lld photo|other=Exported %lld photos
en-GB one=Exported %lld photo|other=Exported %lld photos
es one=Se exportó %lld foto|many=Se exportaron %lld fotos|other=Se exportaron %lld fotos
es-MX one=Se exportó %lld foto|many=Se exportaron %lld fotos|other=Se exportaron %lld fotos
fi one=Vietiin %lld kuva|other=Vietiin %lld kuvaa
fr one=%lld photo exportée|many=%lld photos exportées|other=%lld photos exportées
fr-CA one=%lld photo exportée|many=%lld photos exportées|other=%lld photos exportées
he one=יוצאה %lld תמונה|two=יוצאו %lld תמונות|many=יוצאו %lld תמונות|other=יוצאו %lld תמונות
hi one=%lld फ़ोटो निर्यात की गई|other=%lld फ़ोटो निर्यात की गईं
hr one=Izvezena je %lld fotografija|few=Izvezene su %lld fotografije|many=Izvezeno je %lld fotografija|other=Izvezeno je %lld fotografija
hu one=%lld fotó exportálva|other=%lld fotó exportálva
id other=%lld foto diekspor
it one=Esportata %lld foto|many=Esportate %lld foto|other=Esportate %lld foto
ja other=%lld 枚の写真を書き出しました
ko other=사진 %lld장을 내보냈습니다
ms other=%lld foto dieksport
nb one=Eksporterte %lld bilde|other=Eksporterte %lld bilder
nl one=%lld foto geëxporteerd|other=%lld foto’s geëxporteerd
pl one=Wyeksportowano %lld zdjęcie|few=Wyeksportowano %lld zdjęcia|many=Wyeksportowano %lld zdjęć|other=Wyeksportowano %lld zdjęć
pt-BR one=%lld foto exportada|many=%lld fotos exportadas|other=%lld fotos exportadas
pt-PT one=Exportada %lld fotografia|many=Exportadas %lld fotografias|other=Exportadas %lld fotografias
ro one=S-a exportat %lld fotografie|few=S-au exportat %lld fotografii|other=S-au exportat %lld de fotografii
ru one=Экспортирована %lld фотография|few=Экспортированы %lld фотографии|many=Экспортировано %lld фотографий|other=Экспортировано %lld фотографий
sk one=Exportovaná je %lld fotografia|few=Exportované sú %lld fotografie|many=Exportovaných je %lld fotografií|other=Exportovaných je %lld fotografií
sv one=Exporterade %lld foto|other=Exporterade %lld foton
th other=ส่งออกรูปภาพ %lld รูป
tr one=%lld fotoğraf dışa aktarıldı|other=%lld fotoğraf dışa aktarıldı
uk one=Експортовано %lld фотографію|few=Експортовано %lld фотографії|many=Експортовано %lld фотографій|other=Експортовано %lld фотографій
vi other=Đã xuất %lld ảnh
zh-Hans other=已导出 %lld 张照片
zh-Hant other=已匯出 %lld 張照片
""",
    "journal.entries.count": """
en one=%lld entry|other=%lld entries
ar zero=%lld مدخل|one=%lld مدخل|two=%lld مدخلان|few=%lld مداخل|many=%lld مدخلاً|other=%lld مدخل
bg one=%lld запис|other=%lld записа
ca one=%lld entrada|other=%lld entrades
cs one=%lld záznam|few=%lld záznamy|many=%lld záznamu|other=%lld záznamů
da one=%lld indlæg|other=%lld indlæg
de one=%lld Eintrag|other=%lld Einträge
el one=%lld καταχώριση|other=%lld καταχωρίσεις
en-AU one=%lld entry|other=%lld entries
en-CA one=%lld entry|other=%lld entries
en-GB one=%lld entry|other=%lld entries
es one=%lld entrada|many=%lld entradas|other=%lld entradas
es-MX one=%lld entrada|many=%lld entradas|other=%lld entradas
fi one=%lld merkintä|other=%lld merkintää
fr one=%lld entrée|many=%lld entrées|other=%lld entrées
fr-CA one=%lld entrée|many=%lld entrées|other=%lld entrées
he one=%lld רשומה|two=%lld רשומות|many=%lld רשומות|other=%lld רשומות
hi one=%lld प्रविष्टि|other=%lld प्रविष्टियाँ
hr one=%lld unos|few=%lld unosa|many=%lld unosa|other=%lld unosa
hu one=%lld bejegyzés|other=%lld bejegyzés
id other=%lld entri
it one=%lld voce|many=%lld voci|other=%lld voci
ja other=%lld 件
ko other=%lld개 항목
ms other=%lld entri
nb one=%lld oppføring|other=%lld oppføringer
nl one=%lld item|other=%lld items
pl one=%lld wpis|few=%lld wpisy|many=%lld wpisów|other=%lld wpisów
pt-BR one=%lld entrada|many=%lld entradas|other=%lld entradas
pt-PT one=%lld entrada|many=%lld entradas|other=%lld entradas
ro one=%lld intrare|few=%lld intrări|other=%lld de intrări
ru one=%lld запись|few=%lld записи|many=%lld записей|other=%lld записей
sk one=%lld záznam|few=%lld záznamy|many=%lld záznamov|other=%lld záznamov
sv one=%lld inlägg|other=%lld inlägg
th other=%lld รายการ
tr one=%lld kayıt|other=%lld kayıt
uk one=%lld запис|few=%lld записи|many=%lld записів|other=%lld записів
vi other=%lld mục
zh-Hans other=%lld 条
zh-Hant other=%lld 筆
""",
}

INFOPLIST_EXISTING = {
    "NSMicrophoneUsageDescription": """
en PhotoJournal uses the microphone to record voice notes for your entries.
ar يستخدم PhotoJournal الميكروفون لتسجيل الملاحظات الصوتية لإدخالاتك.
bg PhotoJournal използва микрофона, за да записва гласови бележки към записите ви.
ca PhotoJournal utilitza el micròfon per gravar notes de veu per a les teves entrades.
cs PhotoJournal používá mikrofon k nahrávání hlasových poznámek k vašim záznamům.
da PhotoJournal bruger mikrofonen til at optage stemmenoter til dine indlæg.
de PhotoJournal nutzt das Mikrofon, um Sprachnotizen zu deinen Einträgen aufzunehmen.
el Το PhotoJournal χρησιμοποιεί το μικρόφωνο για να ηχογραφεί φωνητικές σημειώσεις για τις καταχωρίσεις σου.
en-AU PhotoJournal uses the microphone to record voice notes for your entries.
en-CA PhotoJournal uses the microphone to record voice notes for your entries.
en-GB PhotoJournal uses the microphone to record voice notes for your entries.
es PhotoJournal usa el micrófono para grabar notas de voz en tus entradas.
es-MX PhotoJournal usa el micrófono para grabar notas de voz en tus entradas.
fi PhotoJournal käyttää mikrofonia äänimuistiinpanojen tallentamiseen merkintöihisi.
fr PhotoJournal utilise le micro pour enregistrer des notes vocales dans vos entrées.
fr-CA PhotoJournal utilise le microphone pour enregistrer des notes vocales dans vos entrées.
he PhotoJournal משתמש במיקרופון כדי להקליט הערות קוליות לרשומות שלך.
hi PhotoJournal आपकी प्रविष्टियों के लिए वॉइस नोट रिकॉर्ड करने के लिए माइक्रोफ़ोन का उपयोग करता है।
hr PhotoJournal koristi mikrofon za snimanje glasovnih bilješki uz vaše unose.
hu A PhotoJournal a mikrofont használja, hogy hangjegyzeteket rögzítsen a bejegyzéseidhez.
id PhotoJournal menggunakan mikrofon untuk merekam catatan suara untuk entri Anda.
it PhotoJournal usa il microfono per registrare note vocali nelle tue voci.
ja PhotoJournal は、エントリーに添える音声メモを録音するためにマイクを使用します。
ko PhotoJournal은 항목에 덧붙일 음성 메모를 녹음하기 위해 마이크를 사용합니다.
ms PhotoJournal menggunakan mikrofon untuk merakam nota suara bagi entri anda.
nb PhotoJournal bruker mikrofonen til å ta opp talenotater til oppføringene dine.
nl PhotoJournal gebruikt de microfoon om spraaknotities bij je items op te nemen.
pl PhotoJournal używa mikrofonu, aby nagrywać notatki głosowe do Twoich wpisów.
pt-BR O PhotoJournal usa o microfone para gravar notas de voz nas suas entradas.
pt-PT O PhotoJournal utiliza o microfone para gravar notas de voz nas suas entradas.
ro PhotoJournal folosește microfonul pentru a înregistra note vocale la intrările tale.
ru PhotoJournal использует микрофон, чтобы записывать голосовые заметки к вашим записям.
sk PhotoJournal používa mikrofón na nahrávanie hlasových poznámok k vašim záznamom.
sv PhotoJournal använder mikrofonen för att spela in röstanteckningar till dina inlägg.
th PhotoJournal ใช้ไมโครโฟนเพื่อบันทึกโน้ตเสียงสำหรับรายการของคุณ
tr PhotoJournal, girişlerin için sesli notlar kaydetmek amacıyla mikrofonu kullanır.
uk PhotoJournal використовує мікрофон, щоб записувати голосові нотатки до ваших записів.
vi PhotoJournal sử dụng micrô để ghi âm ghi chú thoại cho các mục nhật ký của bạn.
zh-Hans PhotoJournal 使用麦克风为你的日记条目录制语音备注。
zh-Hant PhotoJournal 使用麥克風為你的日記項目錄製語音備註。
""",
    "NSFaceIDUsageDescription": """
en PhotoJournal uses Face ID to unlock your private albums.
ar يستخدم PhotoJournal Face ID لفتح ألبوماتك الخاصة.
bg PhotoJournal използва Face ID, за да отключва личните ви албуми.
ca PhotoJournal utilitza Face ID per desbloquejar els teus àlbums privats.
cs PhotoJournal používá Face ID k odemknutí vašich soukromých alb.
da PhotoJournal bruger Face ID til at låse dine private albummer op.
de PhotoJournal nutzt Face ID, um deine privaten Alben zu entsperren.
el Το PhotoJournal χρησιμοποιεί το Face ID για να ξεκλειδώνει τα ιδιωτικά άλμπουμ σου.
en-AU PhotoJournal uses Face ID to unlock your private albums.
en-CA PhotoJournal uses Face ID to unlock your private albums.
en-GB PhotoJournal uses Face ID to unlock your private albums.
es PhotoJournal usa Face ID para desbloquear tus álbumes privados.
es-MX PhotoJournal usa Face ID para desbloquear tus álbumes privados.
fi PhotoJournal käyttää Face ID:tä yksityisten albumiesi lukituksen avaamiseen.
fr PhotoJournal utilise Face ID pour déverrouiller vos albums privés.
fr-CA PhotoJournal utilise Face ID pour déverrouiller vos albums privés.
he PhotoJournal משתמש ב-Face ID כדי לבטל את נעילת האלבומים הפרטיים שלך.
hi PhotoJournal आपके निजी एल्बम अनलॉक करने के लिए Face ID का उपयोग करता है।
hr PhotoJournal koristi Face ID za otključavanje vaših privatnih albuma.
hu A PhotoJournal a Face ID-t használja a privát albumaid feloldásához.
id PhotoJournal menggunakan Face ID untuk membuka kunci album pribadi Anda.
it PhotoJournal usa Face ID per sbloccare i tuoi album privati.
ja PhotoJournal は Face ID を使って、非公開のアルバムをロック解除します。
ko PhotoJournal은 Face ID를 사용해 비공개 앨범의 잠금을 해제합니다.
ms PhotoJournal menggunakan Face ID untuk membuka kunci album peribadi anda.
nb PhotoJournal bruker Face ID til å låse opp de private albumene dine.
nl PhotoJournal gebruikt Face ID om je privéalbums te ontgrendelen.
pl PhotoJournal używa Face ID, aby odblokować Twoje prywatne albumy.
pt-BR O PhotoJournal usa o Face ID para desbloquear seus álbuns privados.
pt-PT O PhotoJournal utiliza o Face ID para desbloquear os seus álbuns privados.
ro PhotoJournal folosește Face ID pentru a debloca albumele tale private.
ru PhotoJournal использует Face ID, чтобы открывать ваши личные альбомы.
sk PhotoJournal používa Face ID na odomknutie vašich súkromných albumov.
sv PhotoJournal använder Face ID för att låsa upp dina privata album.
th PhotoJournal ใช้ Face ID เพื่อปลดล็อกอัลบั้มส่วนตัวของคุณ
tr PhotoJournal, özel albümlerinin kilidini açmak için Face ID kullanır.
uk PhotoJournal використовує Face ID, щоб відкривати ваші приватні альбоми.
vi PhotoJournal sử dụng Face ID để mở khóa các album riêng tư của bạn.
zh-Hans PhotoJournal 使用 Face ID 解锁你的私密相册。
zh-Hant PhotoJournal 使用 Face ID 解鎖你的私人相簿。
""",
    "NSLocationWhenInUseUsageDescription": """
en PhotoJournal adds the place where each photo was taken to your journal.
ar يضيف PhotoJournal مكان التقاط كل صورة إلى يومياتك.
bg PhotoJournal добавя мястото, където е заснета всяка снимка, към дневника ви.
ca PhotoJournal afegeix al teu diari el lloc on es va fer cada foto.
cs PhotoJournal přidává do vašeho deníku místo, kde byla každá fotka pořízena.
da PhotoJournal tilføjer det sted, hvor hvert foto blev taget, til din dagbog.
de PhotoJournal fügt deinem Tagebuch den Ort hinzu, an dem jedes Foto aufgenommen wurde.
el Το PhotoJournal προσθέτει στο ημερολόγιό σου το μέρος όπου τραβήχτηκε κάθε φωτογραφία.
en-AU PhotoJournal adds the place where each photo was taken to your journal.
en-CA PhotoJournal adds the place where each photo was taken to your journal.
en-GB PhotoJournal adds the place where each photo was taken to your journal.
es PhotoJournal añade a tu diario el lugar donde se tomó cada foto.
es-MX PhotoJournal añade a tu diario el lugar donde se tomó cada foto.
fi PhotoJournal lisää päiväkirjaasi paikan, jossa kukin kuva otettiin.
fr PhotoJournal ajoute à votre journal le lieu où chaque photo a été prise.
fr-CA PhotoJournal ajoute à votre journal l’endroit où chaque photo a été prise.
he PhotoJournal מוסיף ליומן שלך את המקום שבו צולמה כל תמונה.
hi PhotoJournal आपकी जर्नल में हर फ़ोटो लिए जाने की जगह जोड़ता है।
hr PhotoJournal u vaš dnevnik dodaje mjesto na kojem je svaka fotografija snimljena.
hu A PhotoJournal hozzáadja a naplóhoz, hol készült az egyes fényképek.
id PhotoJournal menambahkan lokasi tempat setiap foto diambil ke jurnal Anda.
it PhotoJournal aggiunge al tuo diario il luogo in cui è stata scattata ogni foto.
ja PhotoJournal は、各写真を撮影した場所をジャーナルに追加します。
ko PhotoJournal은 각 사진을 찍은 장소를 저널에 추가합니다.
ms PhotoJournal menambah tempat setiap foto diambil ke dalam jurnal anda.
nb PhotoJournal legger til stedet der hvert bilde ble tatt i dagboken din.
nl PhotoJournal voegt de plek waar elke foto is gemaakt toe aan je dagboek.
pl PhotoJournal dodaje do Twojego dziennika miejsce, w którym wykonano każde zdjęcie.
pt-BR O PhotoJournal adiciona ao seu diário o local onde cada foto foi tirada.
pt-PT O PhotoJournal adiciona ao seu diário o local onde cada fotografia foi tirada.
ro PhotoJournal adaugă în jurnalul tău locul în care a fost făcută fiecare fotografie.
ru PhotoJournal добавляет в ваш дневник место, где был сделан каждый снимок.
sk PhotoJournal pridáva do vášho denníka miesto, kde bola každá fotka urobená.
sv PhotoJournal lägger till platsen där varje foto togs i din dagbok.
th PhotoJournal เพิ่มสถานที่ที่แต่ละภาพถ่ายไว้ลงในเจอร์นัลของคุณ
tr PhotoJournal, çekilen her fotoğrafın konumunu günlüğünüze ekler.
uk PhotoJournal додає до вашого журналу місце, де було зроблено кожне фото.
vi PhotoJournal thêm vào nhật ký của bạn địa điểm chụp từng ảnh.
zh-Hans PhotoJournal 会将每张照片的拍摄地点添加到你的日记中。
zh-Hant PhotoJournal 會將每張照片的拍攝地點加入你的日記中。
""",
}

INFOPLIST_NEW = {
    "NSPhotoLibraryUsageDescription": """
en PhotoJournal needs access to your photo library so you can add photos to your journal.
ar يحتاج PhotoJournal إلى الوصول إلى مكتبة صورك لتتمكن من إضافة الصور إلى يومياتك.
bg PhotoJournal се нуждае от достъп до фотобиблиотеката ви, за да добавяте снимки към дневника си.
ca PhotoJournal necessita accedir a la teva biblioteca de fotos per afegir-hi fotos al teu diari.
cs PhotoJournal potřebuje přístup k vaší knihovně fotek, abyste do deníku mohli přidávat fotky.
da PhotoJournal har brug for adgang til dit fotobibliotek, så du kan tilføje fotos til din dagbog.
de PhotoJournal benötigt Zugriff auf deine Fotomediathek, damit du Fotos zu deinem Tagebuch hinzufügen kannst.
el Το PhotoJournal χρειάζεται πρόσβαση στη βιβλιοθήκη φωτογραφιών σου, ώστε να προσθέτεις φωτογραφίες στο ημερολόγιό σου.
en-AU PhotoJournal needs access to your photo library so you can add photos to your journal.
en-CA PhotoJournal needs access to your photo library so you can add photos to your journal.
en-GB PhotoJournal needs access to your photo library so you can add photos to your journal.
es PhotoJournal necesita acceder a tu biblioteca de fotos para añadir fotos a tu diario.
es-MX PhotoJournal necesita acceder a tu biblioteca de fotos para agregar fotos a tu diario.
fi PhotoJournal tarvitsee pääsyn kuvakirjastoosi, jotta voit lisätä kuvia päiväkirjaasi.
fr PhotoJournal a besoin d’accéder à votre photothèque pour ajouter des photos à votre journal.
fr-CA PhotoJournal doit accéder à votre photothèque pour ajouter des photos à votre journal.
he PhotoJournal זקוקה לגישה לספריית התמונות שלך כדי שתוכל להוסיף תמונות ליומן שלך.
hi जर्नल में फ़ोटो जोड़ने के लिए PhotoJournal को आपकी फ़ोटो लाइब्रेरी तक पहुँच चाहिए।
hr PhotoJournal treba pristup vašoj fototeci kako biste mogli dodavati fotografije u dnevnik.
hu A PhotoJournal-nak hozzá kell férnie a fotótáradhoz, hogy fotókat adhass a naplódhoz.
id PhotoJournal memerlukan akses ke pustaka foto Anda agar Anda dapat menambahkan foto ke jurnal.
it PhotoJournal ha bisogno di accedere alla tua libreria foto per aggiungere foto al tuo diario.
ja ジャーナルに写真を追加できるよう、PhotoJournal が写真ライブラリへのアクセスを必要としています。
ko 저널에 사진을 추가할 수 있도록 PhotoJournal이 사진 보관함에 접근해야 합니다.
ms PhotoJournal memerlukan akses kepada pustaka foto anda supaya anda boleh menambah foto ke dalam jurnal.
nb PhotoJournal trenger tilgang til fotobiblioteket ditt, slik at du kan legge til bilder i dagboken din.
nl PhotoJournal heeft toegang tot je fotobibliotheek nodig om foto’s aan je dagboek toe te voegen.
pl PhotoJournal potrzebuje dostępu do Twojej biblioteki zdjęć, aby można było dodawać zdjęcia do dziennika.
pt-BR O PhotoJournal precisa acessar sua biblioteca de fotos para adicionar fotos ao seu diário.
pt-PT O PhotoJournal precisa de aceder à sua biblioteca de fotografias para adicionar fotografias ao seu diário.
ro PhotoJournal are nevoie de acces la biblioteca ta de fotografii pentru a adăuga fotografii în jurnal.
ru PhotoJournal нужен доступ к вашей медиатеке, чтобы вы могли добавлять фото в дневник.
sk PhotoJournal potrebuje prístup k vašej knižnici fotografií, aby ste mohli do denníka pridávať fotografie.
sv PhotoJournal behöver åtkomst till ditt fotobibliotek så att du kan lägga till foton i din dagbok.
th PhotoJournal ต้องการสิทธิ์เข้าถึงคลังรูปภาพของคุณ เพื่อให้คุณเพิ่มรูปภาพลงในเจอร์นัลได้
tr Günlüğüne fotoğraf ekleyebilmen için PhotoJournal’ın fotoğraf kitaplığına erişmesi gerekir.
uk PhotoJournal потрібен доступ до вашої фототеки, щоб ви могли додавати фото до журналу.
vi PhotoJournal cần quyền truy cập thư viện ảnh của bạn để thêm ảnh vào nhật ký.
zh-Hans PhotoJournal 需要访问你的照片图库，以便你将照片添加到日记中。
zh-Hant PhotoJournal 需要存取你的照片圖庫，才能將照片加入日記中。
""",
    "NSCameraUsageDescription": """
en PhotoJournal uses the camera to take photos for your journal entries.
ar يستخدم PhotoJournal الكاميرا لالتقاط الصور لإدخالات يومياتك.
bg PhotoJournal използва камерата, за да заснема снимки за записите в дневника ви.
ca PhotoJournal utilitza la càmera per fer fotos per a les teves entrades del diari.
cs PhotoJournal používá fotoaparát k pořizování fotek do vašich záznamů v deníku.
da PhotoJournal bruger kameraet til at tage billeder til dine dagbogsindlæg.
de PhotoJournal nutzt die Kamera, um Fotos für deine Tagebucheinträge aufzunehmen.
el Το PhotoJournal χρησιμοποιεί την κάμερα για να τραβάει φωτογραφίες για τις καταχωρίσεις του ημερολογίου σου.
en-AU PhotoJournal uses the camera to take photos for your journal entries.
en-CA PhotoJournal uses the camera to take photos for your journal entries.
en-GB PhotoJournal uses the camera to take photos for your journal entries.
es PhotoJournal usa la cámara para tomar fotos para tus entradas del diario.
es-MX PhotoJournal usa la cámara para tomar fotos para tus entradas del diario.
fi PhotoJournal käyttää kameraa kuvien ottamiseen päiväkirjamerkintöihisi.
fr PhotoJournal utilise l’appareil photo pour prendre des photos pour vos entrées de journal.
fr-CA PhotoJournal utilise la caméra pour prendre des photos pour vos entrées de journal.
he PhotoJournal משתמש במצלמה כדי לצלם תמונות עבור הרשומות שלך ביומן.
hi PhotoJournal आपकी जर्नल प्रविष्टियों के लिए फ़ोटो लेने हेतु कैमरे का उपयोग करता है।
hr PhotoJournal koristi kameru za snimanje fotografija za vaše unose u dnevnik.
hu A PhotoJournal a kamerát használja, hogy fényképeket készítsen a naplóbejegyzéseidhez.
id PhotoJournal menggunakan kamera untuk mengambil foto bagi entri jurnal Anda.
it PhotoJournal usa la fotocamera per scattare foto per le voci del tuo diario.
ja PhotoJournal は、ジャーナルのエントリー用に写真を撮影するためにカメラを使用します。
ko PhotoJournal은 저널 항목에 쓸 사진을 찍기 위해 카메라를 사용합니다.
ms PhotoJournal menggunakan kamera untuk mengambil foto bagi entri jurnal anda.
nb PhotoJournal bruker kameraet til å ta bilder til dagbokoppføringene dine.
nl PhotoJournal gebruikt de camera om foto’s te maken voor je dagboekitems.
pl PhotoJournal używa aparatu, aby robić zdjęcia do wpisów w dzienniku.
pt-BR O PhotoJournal usa a câmera para tirar fotos para as suas entradas do diário.
pt-PT O PhotoJournal utiliza a câmara para tirar fotografias para as suas entradas do diário.
ro PhotoJournal folosește camera pentru a face fotografii pentru intrările tale din jurnal.
ru PhotoJournal использует камеру, чтобы делать фото для записей в дневнике.
sk PhotoJournal používa fotoaparát na fotografovanie pre vaše záznamy v denníku.
sv PhotoJournal använder kameran för att ta foton till dina inlägg i dagboken.
th PhotoJournal ใช้กล้องเพื่อถ่ายภาพสำหรับรายการในเจอร์นัลของคุณ
tr PhotoJournal, günlük girişlerin için fotoğraf çekmek amacıyla kamerayı kullanır.
uk PhotoJournal використовує камеру, щоб робити фото для записів у журналі.
vi PhotoJournal sử dụng máy ảnh để chụp ảnh cho các mục nhật ký của bạn.
zh-Hans PhotoJournal 使用相机为你的日记条目拍摄照片。
zh-Hant PhotoJournal 使用相機為你的日記項目拍攝照片。
""",
}
