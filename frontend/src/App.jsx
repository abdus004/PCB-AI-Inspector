import { useRoute } from './lib/router.js'
import LandingPage from './pages/LandingPage.jsx'
import InspectionPage from './pages/InspectionPage.jsx'
import ResultsPage from './pages/ResultsPage.jsx'

function App() {
  const route = useRoute()
  if (route.name === 'inspect') return <InspectionPage />
  if (route.name === 'results') return <ResultsPage key={route.inspectionId} inspectionId={route.inspectionId} />
  return <LandingPage />
}

export default App
