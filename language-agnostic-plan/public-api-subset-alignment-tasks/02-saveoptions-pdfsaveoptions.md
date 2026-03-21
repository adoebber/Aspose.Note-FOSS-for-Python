# Задача 02. Привести SaveOptions и PdfSaveOptions к subset-совместимости

## Цель

Исправить форму публичного контракта у `SaveOptions` и `PdfSaveOptions` так, чтобы она соответствовала официальному Aspose.Note for .NET в рамках subset-модели.

## Текущее расхождение

- `SaveOptions` является конкретным публичным классом, хотя в .NET это абстрактная базовая сущность
- `PdfSaveOptions` экспонирует Python-only поля `TagIconDir`, `TagIconSize`, `TagIconGap`

## Что нужно сделать

1. Сделать `SaveOptions` неинстанцируемым compatibility-базовым типом либо убрать прямую инстанциацию из публично поддерживаемого сценария.
2. Оставить в `SaveOptions` только .NET-подобные члены:
   - `FontsSubsystem`
   - `PageIndex`
   - `PageCount`
   - `SaveFormat`
3. Удалить из публичного контракта `PdfSaveOptions` поля:
   - `TagIconDir`
   - `TagIconSize`
   - `TagIconGap`
4. Сохранить или добавить .NET-подобные члены `PdfSaveOptions`:
   - `ImageCompression`
   - `JpegQuality`
   - `PageSettings`
   - `PageSplittingAlgorithm`

## Что не считается проблемой в рамках этой задачи

- ограниченный набор значений `SaveFormat`, если это реальное subset-подмножество функциональности и экспортируемые значения совпадают с .NET по смыслу

## Критерии приёмки

- `SaveOptions` не выглядит как обычный пользовательский конкретный класс, несовместимый с .NET shape
- у `PdfSaveOptions` больше нет Python-only публичных полей для tag icon
- публичная форма `SaveOptions` и `PdfSaveOptions` совпадает с subset-контрактом официального API