# План приведения подмножества публичного API в соответствие

Этот документ разбит по принципу: один файл - одна задача.

## Цель

Привести публичный Python API к состоянию subset-совместимости с официальным публичным API Aspose.Note for .NET.

## Правило разбиения

- один файл = одна задача
- в каждом файле есть цель, текущее расхождение, необходимые изменения и критерии приёмки
- общий порядок выполнения определяется этим индексом

## Порядок выполнения

1. [01-compatibility-matrix.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/01-compatibility-matrix.md)
2. [02-saveoptions-pdfsaveoptions.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/02-saveoptions-pdfsaveoptions.md)
3. [03-notetag.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/03-notetag.md)
4. [04-textstyle.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/04-textstyle.md)
5. [05-richtext.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/05-richtext.md)
6. [06-exported-types-review.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/06-exported-types-review.md)
7. [07-compatibility-tests.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/07-compatibility-tests.md)
8. [08-readme-and-release-strategy.md](/d:/Aspose/Aspose.Note/aspose-note-for-python/language-agnostic-plan/public-api-subset-alignment-tasks/08-readme-and-release-strategy.md)

## Общие правила совместимости

1. Публичные экспорты из `aspose.note` определяют поддерживаемую compatibility-поверхность.
2. Если тип из .NET экспортируется в Python под тем же именем, его публичный контракт должен оставаться subset-версией .NET-контракта.
3. Удаление неподдерживаемых публичных Python-only членов предпочтительнее, чем сохранение расходящегося API.
4. Неподдерживаемая .NET-функциональность должна по возможности падать в runtime с типизированным compatibility-исключением, а не исчезать из публичной формы типа.
5. Объединение overload в Python-стиле допустимо.
6. Отсутствие .NET interfaces, generics и CLR-специфичных деталей реализации допустимо.
7. Ограниченный набор enum-значений допустим, если это реальное subset-подмножество функциональности .NET, а сами экспортируемые значения не противоречат официальному API.

## Definition of Done

- Экспортируемые Python compatibility-типы являются реальным subset-подмножеством официального публичного API Aspose.Note for .NET.
- Публичные Python-only члены на compatibility-типах с именами из .NET удалены или скрыты из поддерживаемого контракта.
- Неподдерживаемые возможности падают в runtime, а не маскируются несовместимыми Python-only публичными контрактами.
- Исправленный compatibility-контракт защищён автоматическими тестами.