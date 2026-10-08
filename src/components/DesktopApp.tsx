import { useEffect } from 'react'
import markup from '../legacy/desktop.html?raw'
import { PixiSky } from './PixiSky'
import { Guestbook } from './Guestbook'

/** Progressive React migration: preserve the proven 2.0 DOM shell and desktop UI,
 * while new modules are native React/Motion/Pixi. This is not a full legacy rewrite. */
export function DesktopApp() {
  useEffect(() => { void import('../legacy/desktop.js') }, [])
  return <>
    <div id="app" dangerouslySetInnerHTML={{ __html: markup }} />
    <PixiSky />
    <Guestbook />
  </>
}
