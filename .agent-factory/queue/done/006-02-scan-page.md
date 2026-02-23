# Task: Implement ScanPage (photo upload + OCR)

## Parent Domain
006-frontend-pages

## Description
Страница загрузки фото чека и запуска OCR.

### UI Flow:
1. Кнопка "Сфотографировать" / "Выбрать из галереи" → `<input type="file" accept="image/*" capture="environment">`
2. Превью загруженных фото (можно удалить каждое)
3. Client-side resize перед upload: canvas API → blob, max 2048px по большей стороне, JPEG quality 0.8
4. MainButton: "Распознать" → upload photos + trigger OCR
5. Loading state: спиннер + "Распознаём чек..."
6. Результат OCR:
   - Список позиций (ItemOut[]) с ценами
   - Итого
   - Если total_mismatch — предупреждение "Сумма позиций не совпадает с итогом чека"
   - Валюта
7. CTA: "Всё верно" → `/session/:code/edit` или сразу "Начать голосование"
8. CTA: "Редактировать" → `/session/:code/edit`

### Photo resize helper:
```typescript
async function resizeImage(file: File, maxSize: number = 2048): Promise<Blob> {
  // canvas resize + JPEG compression
}
```

## Files to Create/Modify
- webapp/src/pages/ScanPage.tsx (modify) — полная реализация
- webapp/src/components/PhotoPreview.tsx (create) — превью фото с кнопкой удаления
- webapp/src/lib/resize.ts (create) — image resize utility

## Dependencies
- 005-03-api-client (useCreateSession, useUploadPhotos, useTriggerOcr)
- 005-02-telegram-sdk (MainButton, haptics)
- 005-05-routing

## Tests Required
- `npm run build`
- Manual testing with actual photos

## Acceptance Criteria
- [ ] Фото загружается с камеры или галереи
- [ ] Превью отображается, можно удалить
- [ ] Client-side resize работает (не отправляем файлы >5MB)
- [ ] OCR запускается, результат отображается
- [ ] Mismatch предупреждение при total_mismatch
- [ ] Навигация на edit/voting
- [ ] MainButton интегрирован
- [ ] Loading states

## Estimated Complexity
L

## Status: in-progress
## Assigned: worker-37726
