import type { ArtDef } from '@/lib/ink/art/types'
import { poses } from '@/lib/ink/art/mascots/poses'
import * as mascotBody from '@/lib/ink/art/mascots/body'
import * as mascotProps from '@/lib/ink/art/mascots/props'

export const mascotBatches = { poses } as const
export const mascot = { ...poses } satisfies Record<string, ArtDef>
export type MascotPose = keyof typeof mascot
export { mascotBody }
export { mascotProps }
