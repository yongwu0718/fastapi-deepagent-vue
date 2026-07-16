declare module 'split-pane-v3' {
  import { DefineComponent } from 'vue'

  interface SplitPaneProps {
    split?: 'vertical' | 'horizontal'
    minPercent?: number
    defaultPercent?: number
    className?: string
  }

  const SplitPane: DefineComponent<SplitPaneProps>

  export default SplitPane
}
