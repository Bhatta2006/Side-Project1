import { underline } from '@/lib/ink/shapes'
import { defineRecipe } from '@/lib/ink/recipes'

export const breadcrumbPageRecipe = defineRecipe<Record<string, never>>({
  id: 'breadcrumb-page',
  kind: 'crumb',
  layers: ['rest'],
  pad: 8,
  draw(ink, { w, h }, _p, ctx) {
    ink.layer('rest', () => {
      if (ctx.calm) underline(ink, 1, h - 5, w - 2, { kind: 'single', pen: 'pencil.fine' })
      else underline(ink, 1, h - 8, w - 2, { kind: 'double', pen: 'blue.fine', opts: { width: 1.1 } })
    })
  },
})
