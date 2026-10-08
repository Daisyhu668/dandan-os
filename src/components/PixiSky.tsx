import { useEffect, useRef } from 'react'
/** PixiJS v8 ambient animation; loads client-only, respects reduced motion. */
export function PixiSky() {
  const mount = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!mount.current || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let gone = false
    let app: import('pixi.js').Application | undefined
    const init = async () => {
      const { Application, Graphics } = await import('pixi.js')
      if (gone || !mount.current) return
      app = new Application()
      await app.init({ resizeTo: mount.current, backgroundAlpha: 0, preference: 'webgl', antialias: true })
      if (gone || !mount.current) { app.destroy(true); return }
      mount.current.appendChild(app.canvas)
      const dots = Array.from({ length: 26 }, (_, i) => {
        const star = new Graphics().circle(0, 0, i % 7 === 0 ? 2.6 : 1.5).fill({ color: i%3 ? 0xffffff : 0xfff1b8, alpha: .7 })
        const x = (i * 73.7 % 100) / 100
        const y = (i * 41.9 % 75) / 100
        star.x = app!.screen.width * x
        star.y = app!.screen.height * y
        app!.stage.addChild(star)
        return { star, x, y, seed: i*2.7 }
      })
      app.ticker.add(({lastTime}) => {
        if (!app) return
        for (const p of dots) {
          p.star.x = app.screen.width*p.x + Math.sin(lastTime*.00017+p.seed)*9
          p.star.y = app.screen.height*p.y + Math.cos(lastTime*.0002+p.seed)*7
          p.star.alpha = .3 + (Math.sin(lastTime*.002+p.seed)+1)*.25
        }
      })
    }
    void init().catch((error) => { console.warn('Pixi layer unavailable:', error) })
    return () => { gone = true; app?.destroy(true) }
  }, [])
  return <div id="cloud-sparkle" ref={mount} aria-hidden="true" />
}
