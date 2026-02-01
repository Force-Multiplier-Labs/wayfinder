import * as k8s from '@kubernetes/client-node';
import { ProjectContext } from '../types';
import { getFullConfig } from '../config';

/**
 * Load project context from Kubernetes cluster as a Custom Resource.
 * Fetches ProjectContext CRD from the specified namespace.
 */
export async function loadFromKubernetes(name: string, namespace?: string): Promise<ProjectContext | undefined> {
    try {
        const kc = new k8s.KubeConfig();
        const config = getFullConfig();

        if (config.kubeconfigPath) {
            kc.loadFromFile(config.kubeconfigPath);
        } else {
            kc.loadFromDefault();
        }

        const k8sApi = kc.makeApiClient(k8s.CustomObjectsApi);

        // ProjectContext CRD details
        const group = 'contextcore.io';
        const version = 'v1';
        const plural = 'projectcontexts';
        const targetNamespace = namespace || 'default';

        const response = await k8sApi.getNamespacedCustomObject(
            group,
            version,
            targetNamespace,
            plural,
            name
        );

        // Extract spec from Kubernetes resource
        const k8sResource = response.body as Record<string, unknown>;
        if (k8sResource && k8sResource.spec) {
            return k8sResource.spec as ProjectContext;
        }

        return undefined;
    } catch {
        // Kubernetes API call failed - return undefined without throwing
        return undefined;
    }
}
