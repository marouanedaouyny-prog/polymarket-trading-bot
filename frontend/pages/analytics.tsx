import { useEffect } from "react";
import { useRouter } from "next/router";

export default function AnalyticsLegacyRoute() {
  const router = useRouter();

  useEffect(() => {
    void router.replace("/markets");
  }, [router]);

  return null;
}

