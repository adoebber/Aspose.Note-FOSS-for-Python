# Задача 04. Привести TextStyle к subset-совместимости

## Цель

Привести `TextStyle` к .NET-подобной публичной форме, убрав лишние публичные storage-style поля и добавив отсутствующие compatibility-свойства.

## Текущее расхождение

Сейчас в публичной поверхности есть лишние поля:

- `Bold`
- `Italic`
- `Underline`
- `Strikethrough`
- `Superscript`
- `Subscript`

При этом отсутствуют части официального контракта, включая:

- `IsHidden`
- `IsMathFormatting`
- потенциально `FontStyle`

## Что нужно сделать

1. Оставить публичными именно .NET-подобные свойства:
   - `IsBold`
   - `IsItalic`
   - `IsUnderline`
   - `IsStrikethrough`
   - `IsSuperscript`
   - `IsSubscript`
2. Убрать из поддерживаемого публичного API storage-style поля.
3. Добавить отсутствующие compatibility-свойства:
   - `IsHidden`
   - `IsMathFormatting`
   - `FontStyle`, если нужно для shape parity
4. Сохранить статические свойства:
   - `Default`
   - `DefaultMsOneNoteTitleTextStyle`
   - `DefaultMsOneNoteTitleDateStyle`
   - `DefaultMsOneNoteTitleTimeStyle`
5. Оставить `Language` как публичную точку совместимости.

## Критерии приёмки

- `TextStyle` выглядит как .NET-подобный property-driven тип
- Python-only флаги больше не входят в поддерживаемый контракт
- ключевые отсутствующие compatibility-свойства присутствуют