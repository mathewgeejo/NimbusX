import { PageHeader, Notice } from "../components/ui";

export function AdministrationView() {
  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="Control-plane status"
        description="Organization administration is intentionally unavailable until identity, tenant isolation, and durable workspace storage are implemented."
      />
      <div className="two-column">
        <section className="surface" aria-labelledby="access-boundary-title">
          <p className="eyebrow">Identity and access</p>
          <h2 id="access-boundary-title">Development access only</h2>
          <p className="subtle">
            The foundation can optionally require a static API key, but it does not implement OIDC,
            user identities, organization membership, role authorization, or row-level tenant isolation.
          </p>
          <Notice tone="warning" title="Do not treat this as a multi-tenant administration console">
            <p>
              The organization header accepted by the development API is not an authorization boundary.
              Production access controls must be implemented before tenant administration, share links, or
              collaboration features are exposed.
            </p>
          </Notice>
        </section>
        <section className="surface" aria-labelledby="dataplane-boundary-title">
          <p className="eyebrow">Hybrid data plane</p>
          <h2 id="dataplane-boundary-title">Heartbeat scaffold only</h2>
          <p className="subtle">
            The private-plane package currently supports a configured outbound heartbeat with mTLS material.
            It is not a job worker and does not yet store source credentials, retain raw data, or return
            derived findings.
          </p>
          <Notice tone="info" title="No tenant configuration loaded">
            <p>
              Authenticated enrollment, credential rotation, signed jobs, and customer-VPC data processing
              require future control-plane endpoints. This browser does not simulate those controls.
            </p>
          </Notice>
        </section>
      </div>
    </>
  );
}