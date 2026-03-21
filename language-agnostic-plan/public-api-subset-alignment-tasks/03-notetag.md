# Задача 03. Привести NoteTag к subset-совместимости

## Цель

Сделать публичный контракт `NoteTag` .NET-подобным по форме, не сохраняя Python-only поля и произвольные отклонения.

## Текущее расхождение

Сейчас публично торчат поля:

- `shape`
- `label`
- `text_color`
- `highlight_color`
- `created`
- `completed`

И присутствует только одна factory:

- `CreateYellowStar()`

Это не соответствует официальной .NET-форме типа `NoteTag`.

## Что нужно сделать

1. Перевести публичный контракт на .NET-подобные свойства:
   - `Label`
   - `Icon`
   - `Status`
   - `Highlight`
   - `CreationTime`
   - `CompletedTime`
   - при необходимости `FontColor`
2. Удалить или скрыть lowercase storage-поля из поддерживаемого публичного API.
3. Добавить subset-подмножество статических factory `Create...`, но только тех, что реально существуют в .NET.
4. Не добавлять кастомные helper-factory на публичный compatibility-тип.

## Критерии приёмки

- у `NoteTag` нет Python-only lowercase-полей в поддерживаемом публичном контракте
- публичные свойства совпадают по форме с .NET-типом
- каждая публичная factory соответствует реальной .NET factory